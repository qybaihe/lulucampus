"""Background state-machine runner for taste imports.

Local hackathon mode: one process-local ThreadPoolExecutor (max_workers from
config), each task creates its own SessionLocal. A future Celery worker can
reuse the same run() entry point.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from onemore.core.config import get_settings
from onemore.core.database import SessionLocal
from onemore.core.errors import AppError
from onemore.core.time import ensure_utc
from onemore.db.models import TasteImportSession
from onemore.modules.taste_profile import analyzer
from onemore.modules.taste_profile.providers import create_provider
from onemore.modules.taste_profile.providers.base import DouyinProvider, ProviderError
from onemore.modules.taste_profile.service import (
    AUTHENTICATED,
    CANCELLED,
    COLLECTING,
    FAILED,
    PHONE_REQUIRED,
    QR_EXPIRED,
    QR_SCANNED,
    READY,
    RESOLVING_PROFILE,
    TERMINAL_STATUSES,
    WAITING_SCAN,
    WAITING_SMS_CODE,
    items_path,
    now_utc,
    remove_runtime_dir,
    runtime_dir_for,
    upsert_taste_profile,
)
from onemore.modules.taste_profile.taxonomy import TAG_DEFINITIONS

logger = logging.getLogger("onemore.taste_profile")

POLL_INTERVAL_SECONDS = 0.4


@dataclass
class PhoneAction:
    kind: str
    value: str
    country_code: str = "86"
    done: threading.Event = field(default_factory=threading.Event)
    error: ProviderError | None = None
    cancelled: bool = False


class TasteImportOrchestrator:
    def __init__(self) -> None:
        self._executor: ThreadPoolExecutor | None = None
        self._running: set[str] = set()
        self._providers: dict[str, DouyinProvider] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._refresh_events: dict[str, threading.Event] = {}
        self._phone_actions: dict[str, queue.Queue[PhoneAction]] = {}
        self._guard = threading.Lock()

    def is_running(self, import_id: str) -> bool:
        with self._guard:
            return import_id in self._running

    def active_count(self) -> int:
        with self._guard:
            return len(self._running)

    def submit(self, import_id: str) -> None:
        with self._guard:
            if import_id in self._running:
                return
            self._running.add(import_id)
            self._cancel_events[import_id] = threading.Event()
            self._refresh_events[import_id] = threading.Event()
            self._phone_actions[import_id] = queue.Queue()
        self._pool().submit(self._run, import_id)

    def cancel(self, import_id: str) -> None:
        with self._guard:
            event = self._cancel_events.get(import_id)
            provider = self._providers.get(import_id)
        if event is not None:
            event.set()
        if provider is not None:
            provider.cancel()

    def request_qr_refresh(self, import_id: str) -> None:
        with self._guard:
            event = self._refresh_events.get(import_id)
        if event is not None:
            event.set()

    def request_sms_code(
        self, import_id: str, phone: str, country_code: str, *, timeout: int = 15
    ) -> None:
        self._run_phone_action(
            import_id,
            PhoneAction(kind="request", value=phone, country_code=country_code),
            timeout=timeout,
        )

    def submit_sms_code(self, import_id: str, code: str, *, timeout: int = 15) -> None:
        self._run_phone_action(
            import_id,
            PhoneAction(kind="submit", value=code),
            timeout=timeout,
        )

    def _run_phone_action(self, import_id: str, action: PhoneAction, *, timeout: int) -> None:
        with self._guard:
            actions = self._phone_actions.get(import_id)
            running = import_id in self._running
        if actions is None or not running:
            raise AppError("IMPORT_INVALID_STATE", "登录任务当前不可用", 409)
        actions.put(action)
        if not action.done.wait(timeout):
            action.cancelled = True
            action.value = ""
            action.country_code = ""
            raise AppError("DOUYIN_PHONE_ACTION_TIMEOUT", "手机号登录操作超时", 504)
        if action.error is not None:
            raise AppError(action.error.code, action.error.message, 422)

    def _pool(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=get_settings().douyin_max_parallel_imports,
                thread_name_prefix="taste-import",
            )
        return self._executor

    def _run(self, import_id: str) -> None:
        provider: DouyinProvider | None = None
        try:
            with SessionLocal() as db:
                session = db.get(TasteImportSession, import_id)
                if session is None or session.status in TERMINAL_STATUSES:
                    return
                profile_url = session.profile_url
            runtime_dir = runtime_dir_for(import_id)
            provider = create_provider(import_id, runtime_dir, get_settings())
            provider.profile_url = profile_url
            with self._guard:
                self._providers[import_id] = provider
            provider.start()
            self._run_state_machine(import_id, provider)
        except ProviderError as exc:
            self._fail(import_id, exc.code, exc.message)
        except AppError as exc:
            self._fail(import_id, exc.code, exc.message)
        except Exception:  # process boundary: persist stable public state
            logger.exception("taste import %s crashed", import_id)
            self._fail(import_id, "DOUYIN_IMPORT_FAILED", "导入过程发生未知错误")
        finally:
            if provider is not None:
                try:
                    provider.cleanup()
                except Exception:
                    logger.exception("taste import cleanup failed for %s", import_id)
            with SessionLocal() as db:
                session = db.get(TasteImportSession, import_id)
                if session is not None and session.status == CANCELLED:
                    remove_runtime_dir(session)
            self._finish(import_id)

    def _run_state_machine(self, import_id: str, provider: DouyinProvider) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None:
                return
            max_items = session.max_items
            task_expires_at = ensure_utc(session.expires_at)
        if self._is_cancelled(import_id):
            return

        version = 0
        qr = provider.prepare_qr(version)
        self._publish_qr(import_id, qr.image_data_url, version, qr.expires_in_seconds)
        if self._is_cancelled(import_id):
            return

        scan_deadline = now_utc() + timedelta(seconds=qr.expires_in_seconds)
        while True:
            self._process_phone_actions(import_id, provider)
            if provider.is_logged_in():
                break
            if provider.is_qr_scanned():
                self._mark_qr_scanned(import_id)
            phone_required = provider.is_phone_verification_required()
            if phone_required:
                self._mark_phone_required(import_id)
            phone_phase = self._phone_phase_active(import_id)
            if self._is_cancelled(import_id):
                return
            if self._consume_refresh(import_id):
                version += 1
                qr = provider.prepare_qr(version)
                self._publish_qr(import_id, qr.image_data_url, version, qr.expires_in_seconds)
                scan_deadline = now_utc() + timedelta(seconds=qr.expires_in_seconds)
                continue
            now = now_utc()
            if not phone_required and not phone_phase and now >= scan_deadline:
                self._mark_status(
                    import_id,
                    QR_EXPIRED,
                    "qr_expired",
                    "二维码已过期，请刷新后重新扫码",
                )
            if now >= task_expires_at:
                self._fail(import_id, "DOUYIN_LOGIN_TIMEOUT", "等待扫码超时，任务已结束")
                return
            time.sleep(POLL_INTERVAL_SECONDS)

        self._mark_status(
            import_id,
            AUTHENTICATED,
            "authenticated",
            "已捕获登录态，正在识别账号",
        )
        if self._is_cancelled(import_id):
            return
        profile = provider.resolve_profile()
        self._store_profile(import_id, profile)
        self._mark_status(
            import_id,
            RESOLVING_PROFILE,
            "resolving_profile",
            "正在识别当前账号",
        )
        if self._is_cancelled(import_id):
            return

        self._mark_status(import_id, COLLECTING, "collecting", "正在采集喜欢内容")
        collection = self._collect_items(import_id, provider, max_items)
        if self._is_cancelled(import_id):
            return
        if collection["items_collected"] == 0:
            self._fail(import_id, "DOUYIN_LIKES_UNAVAILABLE", "未采集到任何喜欢内容")
            return

        self._mark_status(import_id, "ANALYZING", "analyzing", "正在分析兴趣画像")
        self._analyze(import_id, collection)

    def _collect_items(
        self,
        import_id: str,
        provider: DouyinProvider,
        max_items: int,
    ) -> dict[str, Any]:
        path = items_path(runtime_dir_for(import_id))
        seen: set[str] = set()
        api_pages = 0

        def is_cancelled() -> bool:
            return self._is_cancelled(import_id)

        for page in provider.collect(max_items, is_cancelled):
            api_pages = page.api_pages
            if page.items:
                with path.open("a", encoding="utf-8") as handle:
                    for item in page.items:
                        aweme_id = str(item.get("aweme_id") or "")
                        if not aweme_id or aweme_id in seen:
                            continue
                        seen.add(aweme_id)
                        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            summary = {
                "api_pages": page.api_pages,
                "items_collected": len(seen),
                "has_more": bool(page.has_more),
            }
            self._store_collection(import_id, summary)
            if not page.has_more or (max_items and len(seen) >= max_items):
                break
            if is_cancelled():
                break
        return {"items_collected": len(seen), "api_pages": api_pages}

    def _analyze(self, import_id: str, collection: dict[str, Any]) -> None:
        path = items_path(runtime_dir_for(import_id))
        items: list[dict[str, Any]] = []
        if path.is_file():
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        analysis = analyzer.analyze_content(items, api_pages=collection.get("api_pages", 0))
        questions = analyzer.select_questions(analysis)
        # Content baseline is immediately usable; quiz only refines later.
        result = analyzer.build_provisional_result(analysis, items=items, use_llm=True)
        labels = {tag.key: tag.label for tag in TAG_DEFINITIONS}
        candidate_items: list[dict[str, Any]] = [
            {"key": key, "label": labels.get(key, key), "score": score}
            for key, score in analysis.content_scores.items()
        ]
        candidate_tags = sorted(
            candidate_items,
            key=lambda item: item["score"],
            reverse=True,
        )
        snapshot = {
            "item_count": analysis.item_count,
            "content_scores": analysis.content_scores,
            "dimensions": analysis.dimensions,
            "domain_shares": analysis.domain_shares,
            "recent200_domains": analysis.recent200_domains,
            "top_domains": analysis.top_domains,
            "sample_stats": analysis.sample_stats,
        }
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            session.analysis_snapshot = snapshot
            session.candidate_tags = candidate_tags
            session.questions = questions
            session.result_snapshot = result
            session.status = READY
            session.completed_at = now_utc()
            session.error_code = None
            session.error_message = None
            session.progress = {
                "phase": "ready",
                "current": analysis.item_count,
                "total": analysis.item_count,
                "percent": 100.0,
                "message": "画像已生成，可选 3–5 道细化题进一步校准",
            }
            upsert_taste_profile(db, session, result)
            db.commit()

    def _publish_qr(self, import_id: str, data_url: str, version: int, expires_in: int) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            session.qr_image_data_url = data_url
            session.qr_version = version
            session.qr_expires_at = now_utc() + timedelta(seconds=expires_in)
            session.status = WAITING_SCAN
            session.error_code = None
            session.error_message = None
            session.progress = {
                "phase": "waiting_scan",
                "current": 0,
                "total": None,
                "percent": None,
                "message": "请使用抖音扫描二维码并确认登录",
            }
            db.commit()

    def _store_profile(self, import_id: str, profile: dict[str, Any]) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            session.source_profile = profile
            db.commit()

    def _store_collection(self, import_id: str, summary: dict[str, Any]) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            session.collection_summary = summary
            session.progress = {
                "phase": "collecting",
                "current": summary["items_collected"],
                "total": None,
                "percent": None,
                "message": f"已识别 {summary['items_collected']} 条喜欢内容，共 {summary['api_pages']} 页",
            }
            db.commit()

    def _mark_status(
        self, import_id: str, status: str, phase: str, message: str
    ) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            session.status = status
            if status == AUTHENTICATED and session.authenticated_at is None:
                session.authenticated_at = now_utc()
            session.progress = {
                "phase": phase,
                "current": session.collection_summary.get("items_collected", 0)
                if status == COLLECTING
                else 0,
                "total": None,
                "percent": None,
                "message": message,
            }
            db.commit()

    def _fail(self, import_id: str, code: str, message: str) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            session.status = FAILED
            session.error_code = code
            session.error_message = message
            session.progress = {
                "phase": "failed",
                "current": session.collection_summary.get("items_collected", 0),
                "total": None,
                "percent": None,
                "message": message,
            }
            db.commit()

    def _is_cancelled(self, import_id: str) -> bool:
        with self._guard:
            event = self._cancel_events.get(import_id)
        return event is not None and event.is_set()

    def _consume_refresh(self, import_id: str) -> bool:
        with self._guard:
            event = self._refresh_events.get(import_id)
        if event is not None and event.is_set():
            event.clear()
            return True
        return False

    def _process_phone_actions(self, import_id: str, provider: DouyinProvider) -> None:
        with self._guard:
            actions = self._phone_actions.get(import_id)
        if actions is None:
            return
        while True:
            try:
                action = actions.get_nowait()
            except queue.Empty:
                return
            try:
                if action.cancelled:
                    continue
                if action.kind == "request":
                    provider.request_sms_code(action.value, action.country_code)
                else:
                    provider.submit_sms_code(action.value)
            except ProviderError as exc:
                action.error = exc
            finally:
                action.value = ""
                action.country_code = ""
                action.done.set()

    def _phone_phase_active(self, import_id: str) -> bool:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            return session is not None and session.status in {
                QR_SCANNED,
                PHONE_REQUIRED,
                WAITING_SMS_CODE,
            }

    def _mark_phone_required(self, import_id: str) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            if session.status not in {WAITING_SCAN, QR_SCANNED}:
                return
            session.status = PHONE_REQUIRED
            session.progress = {
                "phase": "phone_required",
                "current": 0,
                "total": None,
                "percent": None,
                "message": "二维码已确认，请完成手机号验证",
                "qr_scanned": True,
            }
            db.commit()

    def _mark_qr_scanned(self, import_id: str) -> None:
        with SessionLocal() as db:
            session = db.get(TasteImportSession, import_id)
            if session is None or session.status in TERMINAL_STATUSES:
                return
            if session.status != WAITING_SCAN:
                return
            session.status = QR_SCANNED
            session.progress = {
                "phase": "qr_scanned",
                "current": 0,
                "total": None,
                "percent": None,
                "message": "二维码已扫描，等待手机号验证",
                "qr_scanned": True,
            }
            db.commit()

    def _finish(self, import_id: str) -> None:
        with self._guard:
            self._running.discard(import_id)
            self._providers.pop(import_id, None)
            self._cancel_events.pop(import_id, None)
            self._refresh_events.pop(import_id, None)
            actions = self._phone_actions.pop(import_id, None)
        if actions is not None:
            while True:
                try:
                    action = actions.get_nowait()
                except queue.Empty:
                    break
                action.value = ""
                action.error = ProviderError("IMPORT_INVALID_STATE", "登录任务已经结束")
                action.done.set()


taste_orchestrator = TasteImportOrchestrator()
