from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import unquote

from onemore.core.config import get_settings
from onemore.core.database import SessionLocal
from onemore.core.locks import user_locks
from onemore.db.models import LoginSession, LoginStatus, User
from onemore.hermes.executor import normalize_failure
from onemore.hermes.vault import vault_manager
from onemore.modules.identity import service


class LoginOrchestrator:
    """Run the long-lived Work WeChat login outside the request lifecycle."""

    poll_interval_seconds = 0.25

    @staticmethod
    def _campus_subject(state_dir: Path) -> str | None:
        """Read the stable CAS username cookie without logging or persisting it."""

        try:
            document = json.loads((state_dir / "session.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        cookies = document.get("cookies") if isinstance(document, dict) else None
        if not isinstance(cookies, list):
            return None
        for cookie in cookies:
            if not isinstance(cookie, dict):
                continue
            key = cookie.get("key")
            value = cookie.get("value")
            domain = str(cookie.get("domain") or "").lstrip(".").lower()
            if (
                isinstance(key, str)
                and key.startswith("username_")
                and isinstance(value, str)
                and (domain == "sysu.edu.cn" or domain.endswith(".sysu.edu.cn"))
            ):
                normalized = unquote(value).strip()
                if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@-]{2,127}", normalized):
                    return normalized
        return None

    def run(self, session_id: str) -> None:
        settings = get_settings()
        process: subprocess.Popen[str] | None = None
        provisional_to_purge: str | None = None
        user_id: str | None = None
        started_provisional = False
        finalized = False
        try:
            with SessionLocal() as db:
                login = db.get(LoginSession, session_id)
                if login is None or login.status != LoginStatus.PENDING.value:
                    return
                user_id = login.user_id
                login_user = db.get(User, user_id)
                started_provisional = bool(
                    login_user is not None
                    and login_user.account_status == "pending_identity"
                )

            with (
                user_locks.acquire(user_id),
                vault_manager.mounted(user_id) as state_dir,
            ):
                argv = [
                    settings.sysu_cli,
                    "auth",
                    "workwechat",
                    "--state-dir",
                    str(state_dir),
                    "--timeout",
                    str(settings.executor_login_timeout_seconds),
                ]
                process = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=False,
                    env=os.environ.copy(),
                )
                deadline = time.monotonic() + settings.executor_login_timeout_seconds + 10
                qr_path = state_dir / "qr" / "workwechat-login.png"
                qr_published = False

                while process.poll() is None and time.monotonic() < deadline:
                    if not qr_published and qr_path.is_file():
                        self._publish_qr(session_id, qr_path)
                        qr_published = True
                    if self._is_cancelled(session_id):
                        self._terminate(process)
                        return
                    time.sleep(self.poll_interval_seconds)

                if process.poll() is None:
                    self._terminate(process)
                    self._mark_terminal(session_id, LoginStatus.TIMEOUT.value, "timeout")
                    return

                stdout, stderr = process.communicate(timeout=2)
                if process.returncode == 0:
                    subject = self._campus_subject(state_dir)
                    if subject is None:
                        self._mark_terminal(
                            session_id,
                            LoginStatus.FAILED.value,
                            "identity_unavailable",
                        )
                        return
                    with SessionLocal() as db:
                        completed, provisional_to_purge = service.bind_real_login_identity(
                            db, session_id, subject
                        )
                        if completed.user_id != user_id:
                            vault_manager.persist_session_files(completed.user_id, state_dir)
                else:
                    category = normalize_failure(stderr or stdout, process.returncode)
                    terminal = (
                        LoginStatus.TIMEOUT.value
                        if "timeout" in (stderr or stdout).lower()
                        else LoginStatus.FAILED.value
                    )
                    self._mark_terminal(session_id, terminal, category)
                    return
            # The mounted context has now encrypted the same-user case as well.
            # Only after that succeeds may the one-time token become redeemable.
            with SessionLocal() as db:
                completed = service.finalize_real_login(db, session_id)
                finalized = completed.status == LoginStatus.SUCCESS.value
        except Exception as exc:  # process boundary: persist a stable public category
            if process is not None and process.poll() is None:
                self._terminate(process)
            self._mark_terminal(
                session_id,
                LoginStatus.FAILED.value,
                normalize_failure(str(exc)),
            )
        finally:
            if provisional_to_purge:
                vault_manager.purge_user(provisional_to_purge)
            elif started_provisional and not finalized and user_id:
                vault_manager.purge_user(user_id)

    @staticmethod
    def _publish_qr(session_id: str, qr_path: Path) -> None:
        encoded = base64.b64encode(qr_path.read_bytes()).decode("ascii")
        with SessionLocal() as db:
            service.mark_login_waiting(
                db,
                session_id,
                qr_image_data_url=f"data:image/png;base64,{encoded}",
            )

    @staticmethod
    def _is_cancelled(session_id: str) -> bool:
        with SessionLocal() as db:
            login = db.get(LoginSession, session_id)
            return login is None or login.status == LoginStatus.CANCELLED.value

    @staticmethod
    def _mark_terminal(session_id: str, status: str, category: str) -> None:
        with SessionLocal() as db:
            service.mark_login_terminal(db, session_id, status, category)

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


login_orchestrator = LoginOrchestrator()
