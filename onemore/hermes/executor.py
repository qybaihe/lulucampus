from __future__ import annotations

import json
import os
import subprocess
import threading
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from onemore.core.config import get_settings
from onemore.core.errors import AppError
from onemore.core.locks import SlidingWindowRateLimiter, user_locks
from onemore.hermes.catalog import CATALOG, build_argv
from onemore.hermes.schemas import ActionName, ActionRequest, HermesResult
from onemore.hermes.vault import vault_manager


class CircuitBreaker:
    def __init__(self, threshold: int = 5, cool_down_seconds: int = 120) -> None:
        self.threshold = threshold
        self.cool_down = timedelta(seconds=cool_down_seconds)
        self._guard = threading.Lock()
        self._failures: dict[str, int] = defaultdict(int)
        self._open_until: dict[str, datetime] = {}

    def assert_closed(self, subsystem: str) -> None:
        with self._guard:
            until = self._open_until.get(subsystem)
            if until and until > datetime.now(UTC):
                raise AppError(
                    "SUBSYSTEM_UNAVAILABLE",
                    "校园子系统暂时不可用，请稍后再试",
                    503,
                    {"subsystem": subsystem, "retry_at": until.isoformat()},
                )
            if until:
                self._open_until.pop(subsystem, None)
                self._failures[subsystem] = 0

    def success(self, subsystem: str) -> None:
        with self._guard:
            self._failures[subsystem] = 0

    def failure(self, subsystem: str) -> None:
        with self._guard:
            self._failures[subsystem] += 1
            if self._failures[subsystem] >= self.threshold:
                self._open_until[subsystem] = datetime.now(UTC) + self.cool_down


def normalize_failure(stderr: str, returncode: int | None = None) -> str:
    value = stderr.lower()
    if any(word in value for word in ("login", "session", "cookie", "认证", "登录")):
        return "login_expired"
    if any(word in value for word in ("occupied", "conflict", "已预约", "占用")):
        return "resource_conflict"
    if any(
        word in value
        for word in (
            "multiple venue",
            "matched",
            "ambiguous",
            "invalid",
            "参数",
            "usage:",
        )
    ) or returncode == 4:
        return "invalid_parameters"
    if any(word in value for word in ("timeout", "timed out", "429", "500", "502", "503")):
        return "rate_limited_or_maintenance"
    return "unknown"


class ExecutorPool:
    HEALTH_COMMANDS: dict[str, tuple[list[str], bool]] = {
        "cas": (["jwxt", "status"], True),
        "jwxt": (["jwxt", "status"], True),
        "libic": (["libic", "whoami", "--json"], True),
        "gym": (["gym", "profile", "--json"], True),
        "explore": (["explore", "whoami", "--json"], True),
    }

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self._slots = threading.BoundedSemaphore(settings.executor_global_slots)
        self._limiter = SlidingWindowRateLimiter(settings.executor_per_user_per_minute)
        self._breaker = CircuitBreaker()

    def execute(self, request: ActionRequest, *, server_confirmed: bool = False) -> HermesResult:
        definition = CATALOG[request.action]
        params = request.validated_params()
        self._limiter.check(request.user_id)
        self._breaker.assert_closed(definition.subsystem)

        if self.settings.hermes_mode == "fake":
            return self._fake(request.action, params.model_dump(mode="json"), server_confirmed)

        timeout = (
            self.settings.executor_write_timeout_seconds
            if definition.is_write
            else self.settings.executor_read_timeout_seconds
        )
        with (
            user_locks.acquire(request.user_id),
            self._slots,
            vault_manager.mounted(request.user_id) as state_dir,
        ):
            argv = [
                self.settings.sysu_cli,
                *build_argv(request.action, params, server_confirmed=server_confirmed),
            ]
            if definition.supports_state_dir:
                argv.extend(["--state-dir", str(state_dir)])
            env = os.environ.copy()
            if not definition.supports_state_dir:
                env["HOME"] = str(state_dir)
            try:
                process = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    shell=False,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                self._breaker.failure(definition.subsystem)
                return HermesResult(
                    action=request.action,
                    ok=False,
                    error_category="rate_limited_or_maintenance",
                    data={"message": "执行超时", "timeout_seconds": timeout},
                )

        if process.returncode != 0:
            category = normalize_failure(process.stderr or process.stdout, process.returncode)
            if category in {"rate_limited_or_maintenance", "unknown"}:
                self._breaker.failure(definition.subsystem)
            return HermesResult(
                action=request.action,
                ok=False,
                error_category=category,
                data={"message": "校园系统操作未完成"},
            )

        self._breaker.success(definition.subsystem)
        try:
            data: Any = json.loads(process.stdout)
        except json.JSONDecodeError:
            data = {"text": process.stdout.strip()}
        return HermesResult(action=request.action, ok=True, data=data)

    def check_subsystem(self, user_id: str, subsystem: str) -> tuple[bool, str | None]:
        command = self.HEALTH_COMMANDS.get(subsystem)
        if command is None:
            return False, "unsupported"
        if self.settings.hermes_mode == "fake":
            vault_manager.update_session_health(user_id, subsystem, True, None)
            return True, None

        argv_tail, supports_state_dir = command
        with (
            user_locks.acquire(user_id),
            self._slots,
            vault_manager.mounted(user_id) as state_dir,
        ):
            argv = [self.settings.sysu_cli, *argv_tail]
            if supports_state_dir:
                argv.extend(["--state-dir", str(state_dir)])
            try:
                process = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=self.settings.executor_read_timeout_seconds,
                    check=False,
                    shell=False,
                    env=os.environ.copy(),
                )
            except subprocess.TimeoutExpired:
                category = "rate_limited_or_maintenance"
                self._breaker.failure(subsystem)
                vault_manager.update_session_health(user_id, subsystem, False, category)
                return False, category

        if process.returncode == 0:
            self._breaker.success(subsystem)
            vault_manager.update_session_health(user_id, subsystem, True, None)
            return True, None
        category = normalize_failure(process.stderr or process.stdout, process.returncode)
        self._breaker.failure(subsystem)
        vault_manager.update_session_health(user_id, subsystem, False, category)
        return False, category

    def run_cli_json(
        self,
        user_id: str,
        argv_tail: list[str],
        *,
        subsystem: str = "jwxt",
        timeout_seconds: int | None = None,
        supports_state_dir: bool = True,
    ) -> tuple[Any | None, str | None]:
        """Run an arbitrary sysu-anything command with the user's vault mounted."""

        if self.settings.hermes_mode == "fake":
            return {"items": []}, None
        self._limiter.check(user_id)
        self._breaker.assert_closed(subsystem)
        timeout = timeout_seconds or self.settings.executor_read_timeout_seconds
        with (
            user_locks.acquire(user_id),
            self._slots,
            vault_manager.mounted(user_id) as state_dir,
        ):
            argv = [self.settings.sysu_cli, *argv_tail]
            if supports_state_dir:
                argv.extend(["--state-dir", str(state_dir)])
            env = os.environ.copy()
            if not supports_state_dir:
                env["HOME"] = str(state_dir)
            try:
                process = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    shell=False,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                self._breaker.failure(subsystem)
                return None, "rate_limited_or_maintenance"
        if process.returncode != 0:
            category = normalize_failure(process.stderr or process.stdout, process.returncode)
            if category in {"rate_limited_or_maintenance", "unknown"}:
                self._breaker.failure(subsystem)
            return None, category
        self._breaker.success(subsystem)
        try:
            return json.loads(process.stdout), None
        except json.JSONDecodeError:
            return None, "unknown"

    def fetch_timetable_import(self, user_id: str) -> tuple[dict[str, Any] | None, str | None]:
        """Fetch import-ready occurrences for the private timetable ETL job."""

        if self.settings.hermes_mode == "fake":
            return {"occurrences": [], "entries": [], "termWeeks": 25}, None
        payload, err = self.run_cli_json(
            user_id,
            ["jwxt", "timetable-import", "--json"],
            subsystem="jwxt",
            timeout_seconds=max(60, self.settings.executor_read_timeout_seconds),
        )
        if err:
            return None, err
        if not isinstance(payload, dict) or not isinstance(payload.get("occurrences"), list):
            return None, "invalid_response"
        return payload, None

    def _fake(self, action: ActionName, params: dict[str, Any], confirmed: bool) -> HermesResult:
        now = datetime.now(UTC).isoformat()
        data: Any
        if action == ActionName.TIMETABLE_TODAY:
            data = {"courses": [], "updated_at": now}
        elif action == ActionName.TIMETABLE_FETCH_TERM:
            data = {"weeks_scanned": [params["scan_from"], params["scan_to"]], "courses": []}
        elif action == ActionName.ASSIGNMENT_LIST_UNFINISHED:
            data = {"items": []}
        elif action == ActionName.ROOM_AVAILABLE:
            data = {
                "slots": [
                    {
                        "kind": params["kind"],
                        "room": params.get("room") or "401",
                        "start": "00:00",
                        "end": "23:59",
                        "available": True,
                    }
                ],
                "queried_at": now,
                "params": params,
            }
        elif action == ActionName.GYM_AVAILABLE:
            data = {
                "slots": [
                    {
                        "venue_type": params["venue_type"],
                        "venue": params.get("venue") or "东区 1 号场",
                        "start": "00:00",
                        "end": "23:59",
                        "available": True,
                    }
                ],
                "queried_at": now,
                "params": params,
            }
        elif action in {
            ActionName.ROOM_RESERVE_PREVIEW,
            ActionName.GYM_BOOK_PREVIEW,
            ActionName.SEMINAR_RESERVE_PREVIEW,
        }:
            data = {"preview": params, "requires_confirm": True, "generated_at": now}
        elif action in {
            ActionName.ROOM_RESERVE_COMMIT,
            ActionName.GYM_BOOK_COMMIT,
            ActionName.SEMINAR_RESERVE_COMMIT,
        }:
            if not confirmed:
                return HermesResult(action=action, ok=False, error_category="invalid_parameters")
            data = {
                "reservation_id": f"demo-{abs(hash(json.dumps(params, sort_keys=True))) % 10**10}",
                "confirmed": True,
                "executed_at": now,
            }
        else:
            data = {"items": [], "params": params, "updated_at": now}
        return HermesResult(action=action, ok=True, data=data)


executor_pool = ExecutorPool()
