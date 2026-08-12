"""Data access and state transitions for Douyin taste imports.

Background transitions are driven by the orchestrator worker; request handlers
call the read/sync functions here. Every transition helper accepts an ORM
session so workers and HTTP handlers behave identically.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.errors import AppError, NotFoundError
from onemore.core.time import ensure_utc
from onemore.db.models import Profile, TasteImportSession, TasteProfile, new_id
from onemore.modules.taste_profile import analyzer
from onemore.modules.taste_profile.analyzer import MODEL_VERSION

# Tags synced from Douyin taste stay on the user profile for matching and
# member-visible chips. Keys are namespaced so course-verified tags stay pure.
TASTE_TAG_PREFIX = "taste:"

SOURCE_DOUYIN = "douyin"
SOURCE_PROFILE_KEY = "douyin"

PREPARING_QR = "PREPARING_QR"
WAITING_SCAN = "WAITING_SCAN"
QR_SCANNED = "QR_SCANNED"
PHONE_REQUIRED = "PHONE_REQUIRED"
WAITING_SMS_CODE = "WAITING_SMS_CODE"
AUTHENTICATED = "AUTHENTICATED"
RESOLVING_PROFILE = "RESOLVING_PROFILE"
COLLECTING = "COLLECTING"
ANALYZING = "ANALYZING"
NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
READY = "READY"
QR_EXPIRED = "QR_EXPIRED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"

TERMINAL_STATUSES = {READY, FAILED, CANCELLED}
QR_WAIT_STATUSES = {
    WAITING_SCAN,
    QR_SCANNED,
    PHONE_REQUIRED,
    WAITING_SMS_CODE,
    QR_EXPIRED,
    PREPARING_QR,
}
COOKIE_FLAG_NAMES = {"sessionid", "sessionid_ss", "sid_tt", "sid_guard"}

DEFAULT_TASK_TTL_SECONDS = 60 * 60
MIN_ANSWERS = 3
MAX_QUESTIONS = 5


def runtime_dir_for(import_id: str) -> Path:
    return get_settings().douyin_runtime_root / import_id


def items_path(runtime_dir: Path) -> Path:
    return runtime_dir / "items.jsonl"


def now_utc() -> datetime:
    return datetime.now(UTC)


def normalize_taste_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Public result envelope shared by import.result and /profile/taste/*."""
    if not result:
        return None
    sample = dict(result.get("sample") or {})
    facets = result.get("interest_facets") or sample.get("interest_facets") or []
    return {
        "status": READY,
        "primary_tag": result.get("primary_tag") or {},
        "secondary_tags": result.get("secondary_tags") or [],
        "interest_domains": result.get("interest_domains") or [],
        "interest_facets": facets,
        "dimensions": result.get("dimensions") or {},
        "summary": result.get("summary") or "",
        "persona": result.get("persona") or sample.get("persona"),
        "matching_hints": result.get("matching_hints") or sample.get("matching_hints") or [],
        "confidence": float(result.get("confidence") or 0.0),
        "calibrated": bool(result.get("calibrated", sample.get("calibrated", False))),
        "calibrated_at": result.get("calibrated_at", sample.get("calibrated_at")),
        "sample": sample,
        "source": result.get("source") or SOURCE_DOUYIN,
        "model_version": result.get("model_version") or MODEL_VERSION,
        # Product decision: usable for matching and member display.
        "visibility": "members",
    }


def _tag_entries(result: dict[str, Any]) -> list[tuple[str, str, float]]:
    """Return (storage_key, label, score) for primary + secondary + domain tags."""
    entries: list[tuple[str, str, float]] = []
    seen: set[str] = set()

    def add(raw_key: str | None, label: str | None, score: float) -> None:
        if not raw_key:
            return
        key = raw_key if raw_key.startswith(TASTE_TAG_PREFIX) else f"{TASTE_TAG_PREFIX}{raw_key}"
        if key in seen:
            return
        seen.add(key)
        entries.append((key, label or raw_key, max(0.0, min(1.0, float(score or 0.0)))))

    primary = result.get("primary_tag") or {}
    if isinstance(primary, dict):
        add(primary.get("key"), primary.get("label"), primary.get("score") or 0.8)
    for tag in result.get("secondary_tags") or []:
        if isinstance(tag, dict):
            add(tag.get("key"), tag.get("label"), tag.get("score") or 0.5)
    for domain in result.get("interest_domains") or []:
        if isinstance(domain, dict):
            add(
                f"domain:{domain.get('key')}",
                domain.get("label"),
                domain.get("score") or 0.4,
            )
    return entries


def public_interest_tags(db: Session, user_id: str, *, limit: int = 6) -> list[str]:
    """Member-visible interest chips derived from the stored taste profile."""
    profile = db.get(TasteProfile, user_id)
    if profile is None:
        return []
    labels: list[str] = []
    primary = profile.primary_tag or {}
    if isinstance(primary, dict) and primary.get("label"):
        labels.append(str(primary["label"]))
    for tag in profile.secondary_tags or []:
        if isinstance(tag, dict) and tag.get("label"):
            labels.append(str(tag["label"]))
    for domain in profile.interest_domains or []:
        if isinstance(domain, dict) and domain.get("label"):
            labels.append(str(domain["label"]))
    # Preserve order, drop empties/dupes.
    ordered: list[str] = []
    for label in labels:
        text = label.strip()
        if text and text not in ordered:
            ordered.append(text)
        if len(ordered) >= limit:
            break
    return ordered


def taste_feature_set(db: Session, user_id: str) -> set[str]:
    """Stable feature keys used by matching (tag + domain keys)."""
    profile = db.get(TasteProfile, user_id)
    if profile is None:
        return set()
    keys: set[str] = set()
    primary = profile.primary_tag or {}
    if isinstance(primary, dict) and primary.get("key"):
        keys.add(str(primary["key"]))
    for tag in profile.secondary_tags or []:
        if isinstance(tag, dict) and tag.get("key"):
            keys.add(str(tag["key"]))
    for domain in profile.interest_domains or []:
        if isinstance(domain, dict) and domain.get("key"):
            keys.add(f"domain:{domain['key']}")
    return keys


def sync_taste_to_user_profile(
    db: Session, user_id: str, result: dict[str, Any]
) -> Profile:
    """Persist taste as durable user tags for matching and later social display.

    - interest_domains: domain labels for profile surface
    - self_reported_tags: namespaced taste keys (taste:*) so they never collide
      with course-verified capability keys
    - capability_vector: scores for matching jaccard / complementary coverage
    """
    from onemore.modules.profile.service import ensure_profile

    profile = ensure_profile(db, user_id)
    entries = _tag_entries(result)
    taste_keys = {key for key, _, _ in entries}

    # Drop previous taste:* tags, keep user-edited self-reported course tags.
    kept_self = [
        key
        for key in (profile.self_reported_tags or [])
        if not str(key).startswith(TASTE_TAG_PREFIX)
    ]
    profile.self_reported_tags = sorted({*kept_self, *taste_keys})

    vector = {
        key: value
        for key, value in (profile.capability_vector or {}).items()
        if not str(key).startswith(TASTE_TAG_PREFIX)
    }
    for key, _label, score in entries:
        # Primary-ish weights stay visible in matching.
        vector[key] = max(vector.get(key, 0.0), round(0.35 + 0.65 * score, 4))
    profile.capability_vector = vector

    domains = result.get("interest_domains") or []
    domain_labels: list[str] = []
    for item in domains:
        if isinstance(item, dict):
            label = item.get("label") or item.get("key")
            if label:
                domain_labels.append(str(label))
    # Prefer taste domains; keep any prior non-empty academic domains if taste empty.
    if domain_labels:
        profile.interest_domains = domain_labels[:12]
    return profile


def clear_taste_from_user_profile(db: Session, user_id: str) -> None:
    profile = db.get(Profile, user_id)
    if profile is None:
        return
    profile.self_reported_tags = [
        key
        for key in (profile.self_reported_tags or [])
        if not str(key).startswith(TASTE_TAG_PREFIX)
    ]
    profile.capability_vector = {
        key: value
        for key, value in (profile.capability_vector or {}).items()
        if not str(key).startswith(TASTE_TAG_PREFIX)
    }


def _session_view(session: TasteImportSession) -> dict[str, Any]:
    error = None
    if session.error_code:
        error = {"code": session.error_code, "message": session.error_message or ""}
    collection = None
    if session.collection_summary:
        collection = {
            "api_pages": session.collection_summary.get("api_pages", 0),
            "items_collected": session.collection_summary.get("items_collected", 0),
            "has_more": session.collection_summary.get("has_more", True),
        }
    calibrated = bool((session.result_snapshot or {}).get("calibrated"))
    # Embed quiz JSON when READY so iOS can load questions without a second round-trip.
    questions = None
    if session.status in {READY, NEEDS_CONFIRMATION} and session.questions and not calibrated:
        questions = questions_payload(session)
    return {
        "id": session.id,
        "source": session.source,
        "status": session.status,
        "qr_image_data_url": session.qr_image_data_url,
        "qr_version": session.qr_version,
        "qr_expires_at": ensure_utc(session.qr_expires_at) if session.qr_expires_at else None,
        "expires_at": ensure_utc(session.expires_at),
        "source_profile": session.source_profile or None,
        "progress": session.progress,
        "collection": collection,
        "candidate_tags": session.candidate_tags,
        "question_count": len(session.questions or []),
        "questions": questions,
        "result": normalize_taste_result(session.result_snapshot),
        "error": error,
    }


def _ensure_owner(db: Session, import_id: str, user_id: str) -> TasteImportSession:
    session = db.scalar(
        select(TasteImportSession).where(
            TasteImportSession.id == import_id, TasteImportSession.user_id == user_id
        )
    )
    if session is None:
        raise NotFoundError("导入任务", import_id)
    return session


def _find_active_session(db: Session, user_id: str) -> TasteImportSession | None:
    return db.scalar(
        select(TasteImportSession)
        .where(
            TasteImportSession.user_id == user_id,
            TasteImportSession.status.not_in(TERMINAL_STATUSES),
        )
        .order_by(TasteImportSession.created_at.desc())
    )


def create_import(
    db: Session,
    user_id: str,
    *,
    profile_url: str | None,
    max_items: int,
    force: bool,
    orchestrator,
) -> TasteImportSession:
    from onemore.core.config import get_settings

    settings = get_settings()
    if not settings.douyin_import_enabled:
        raise AppError("DOUYIN_IMPORT_DISABLED", "抖音兴趣导入功能未开启", 403)
    existing = _find_active_session(db, user_id)
    if existing is not None and not force:
        return existing
    if existing is not None:
        existing.status = CANCELLED
        existing.error_code = None
        existing.error_message = None
        orchestrator.cancel(existing.id)
        db.commit()
    session = TasteImportSession(
        id=f"imp_{new_id().replace('-', '')[:28]}",
        user_id=user_id,
        source=SOURCE_DOUYIN,
        status=PREPARING_QR,
        profile_url=profile_url,
        max_items=max_items,
        expires_at=now_utc() + timedelta(seconds=DEFAULT_TASK_TTL_SECONDS),
        progress={
            "phase": "preparing_qr",
            "current": 0,
            "total": None,
            "percent": None,
            "message": "正在打开抖音登录页",
        },
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_import(db: Session, import_id: str, user_id: str) -> TasteImportSession:
    session = _ensure_owner(db, import_id, user_id)
    _apply_lazy_timeouts(db, session)
    return session


def to_view(session: TasteImportSession) -> dict[str, Any]:
    return _session_view(session)


def _apply_lazy_timeouts(db: Session, session: TasteImportSession) -> None:
    now = now_utc()
    if session.status in QR_WAIT_STATUSES and now > _as_utc(session.expires_at):
        session.status = FAILED
        session.error_code = "DOUYIN_LOGIN_TIMEOUT"
        session.error_message = "等待扫码超时，任务已结束"
        db.commit()
    elif session.status in {AUTHENTICATED, RESOLVING_PROFILE, COLLECTING, ANALYZING}:
        return
    elif session.status == NEEDS_CONFIRMATION and now > _as_utc(session.expires_at):
        session.status = FAILED
        session.error_code = "IMPORT_TASK_EXPIRED"
        session.error_message = "任务已过期，请重新导入"
        db.commit()


def cancel_import(db: Session, import_id: str, user_id: str, orchestrator) -> TasteImportSession:
    session = _ensure_owner(db, import_id, user_id)
    if session.status not in TERMINAL_STATUSES:
        session.status = CANCELLED
        db.commit()
    orchestrator.cancel(import_id)
    if not orchestrator.is_running(import_id):
        remove_runtime_dir(session)
    db.refresh(session)
    return session


def request_qr_refresh(
    db: Session, import_id: str, user_id: str, orchestrator
) -> TasteImportSession:
    session = _ensure_owner(db, import_id, user_id)
    if session.status not in {WAITING_SCAN, QR_EXPIRED, PREPARING_QR}:
        raise AppError("IMPORT_INVALID_STATE", "当前状态不允许刷新二维码", 409)
    if session.status == PREPARING_QR:
        return session
    session.status = PREPARING_QR
    session.progress = {
        "phase": "preparing_qr",
        "current": 0,
        "total": None,
        "percent": None,
        "message": "正在生成新二维码",
    }
    db.commit()
    orchestrator.request_qr_refresh(import_id)
    db.refresh(session)
    return session


def mark_phone_code_sent(
    db: Session, import_id: str, user_id: str, phone_masked: str
) -> TasteImportSession:
    session = _ensure_owner(db, import_id, user_id)
    if session.status not in {QR_SCANNED, PHONE_REQUIRED}:
        raise AppError("DOUYIN_SCAN_REQUIRED", "请先完成抖音二维码扫码", 409)
    session.status = WAITING_SMS_CODE
    session.progress = {
        "phase": "waiting_sms_code",
        "current": 0,
        "total": None,
        "percent": None,
        "message": "短信验证码已发送，请输入验证码",
        "phone_masked": phone_masked,
        "code_sent": True,
    }
    db.commit()
    db.refresh(session)
    return session


def phone_login_view(session: TasteImportSession) -> dict[str, Any]:
    return {
        "phone_masked": session.progress.get("phone_masked"),
        "code_sent": bool(session.progress.get("code_sent", False)),
    }


def get_items(
    db: Session,
    import_id: str,
    user_id: str,
    *,
    cursor: int,
    limit: int,
) -> dict[str, Any]:
    _ensure_owner(db, import_id, user_id)
    path = items_path(runtime_dir_for(import_id))
    rows: list[dict[str, Any]] = []
    if path.is_file():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    page = rows[cursor : cursor + limit]
    next_cursor = cursor + len(page)
    return {
        "items": page,
        "next_cursor": next_cursor,
        "has_more": next_cursor < len(rows),
    }


def questions_payload(session: TasteImportSession) -> dict[str, Any]:
    """Stable JSON contract for iOS: load questions → render → POST answers."""
    return {
        "schema_version": "taste-quiz-v1",
        "import_id": session.id,
        "candidate_tags": session.candidate_tags or [],
        "questions": session.questions or [],
        "calibrated": bool((session.result_snapshot or {}).get("calibrated")),
        "optional": True,
        "min_answers": MIN_ANSWERS,
        "max_answers": MAX_QUESTIONS,
        "intro": "根据你的喜欢内容，选 3–5 道题帮 AI 把兴趣画像说得更准。",
        "submit_path": f"/profile/imports/{session.id}/answers",
    }


def get_questions(
    db: Session, import_id: str, user_id: str
) -> dict[str, Any]:
    session = _ensure_owner(db, import_id, user_id)
    # READY after analysis; NEEDS_CONFIRMATION kept for any legacy in-flight tasks.
    if session.status not in {NEEDS_CONFIRMATION, READY}:
        raise AppError(
            "IMPORT_INVALID_STATE",
            "当前状态还没有可用的细化问题",
            409,
        )
    if not session.questions:
        raise AppError(
            "IMPORT_INVALID_STATE",
            "当前导入还没有生成细化问题",
            409,
        )
    return questions_payload(session)


def _load_session_items(session: TasteImportSession) -> list[dict[str, Any]]:
    path = items_path(runtime_dir_for(session.id))
    if not path.is_file():
        return []
    items: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def submit_answers(
    db: Session,
    import_id: str,
    user_id: str,
    answers: list[dict[str, str]],
) -> dict[str, Any]:
    """Apply quiz answers → rule refine → AI re-narrate for higher precision."""
    session = _ensure_owner(db, import_id, user_id)
    if session.status not in {NEEDS_CONFIRMATION, READY}:
        raise AppError(
            "IMPORT_INVALID_STATE",
            "当前状态不允许提交细化答案",
            409,
        )
    valid_ids = {question["id"] for question in session.questions}
    valid_options = {
        question["id"]: {option["id"] for option in question["options"]}
        for question in session.questions
    }
    if not MIN_ANSWERS <= len(answers) <= MAX_QUESTIONS:
        raise AppError(
            "INVALID_QUIZ_ANSWER",
            f"需要回答 {MIN_ANSWERS}–{MAX_QUESTIONS} 道题",
            422,
        )
    for answer in answers:
        question_id = answer.get("question_id")
        option_id = answer.get("option_id")
        if question_id not in valid_ids or option_id not in valid_options.get(question_id, set()):
            raise AppError(
                "INVALID_QUIZ_ANSWER",
                "问题或选项不存在",
                422,
                {"question_id": question_id, "option_id": option_id},
            )
    analysis = analyzer.ContentAnalysis(
        item_count=session.analysis_snapshot.get("item_count", 0),
        content_scores=session.analysis_snapshot.get("content_scores", {}),
        dimensions=session.analysis_snapshot.get("dimensions", {}),
        domain_shares=session.analysis_snapshot.get("domain_shares", {}),
        recent200_domains=session.analysis_snapshot.get("recent200_domains", {}),
        top_domains=session.analysis_snapshot.get("top_domains", []),
        sample_stats=session.analysis_snapshot.get("sample_stats", {}),
    )
    # 1) Deterministic refine from answers (tag/domain/facet deltas).
    result = analyzer.score_answers(analysis, session.questions, answers)

    # 2) AI rewrite with quiz context for more precise summary/persona/hints.
    items = _load_session_items(session)
    try:
        from onemore.modules.taste_profile.llm_enrich import enrich_provisional_profile

        result = enrich_provisional_profile(
            result,
            items,
            quiz_answers=answers,
            quiz_questions=session.questions,
        )
    except Exception:
        result.setdefault("sample", {})
        if isinstance(result["sample"], dict):
            result["sample"].setdefault("generation", "rule")

    result["calibrated"] = True
    if isinstance(result.get("sample"), dict):
        result["sample"]["calibrated"] = True
        result["sample"]["refined_with_quiz"] = True

    session.answers = {answer["question_id"]: answer["option_id"] for answer in answers}
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
        "message": "已根据你的回答用 AI 精修画像",
    }
    upsert_taste_profile(db, session, result)
    db.commit()
    db.refresh(session)
    return normalize_taste_result(result) or result


def upsert_taste_profile(
    db: Session, session: TasteImportSession, result: dict[str, Any]
) -> TasteProfile:
    profile = db.get(TasteProfile, session.user_id)
    if profile is None:
        profile = TasteProfile(user_id=session.user_id)
        db.add(profile)
    profile.source = SOURCE_DOUYIN
    profile.source_import_id = session.id
    profile.primary_tag = result["primary_tag"]
    profile.secondary_tags = result["secondary_tags"]
    profile.interest_domains = result["interest_domains"]
    profile.dimensions = result["dimensions"]
    profile.summary = result["summary"]
    profile.confidence = result["confidence"]
    # Pack calibrated / interest_facets into sample_summary to avoid a migration.
    sample = dict(result.get("sample") or {})
    sample["calibrated"] = bool(result.get("calibrated", sample.get("calibrated", False)))
    sample["calibrated_at"] = result.get("calibrated_at", sample.get("calibrated_at"))
    sample["interest_facets"] = result.get(
        "interest_facets", sample.get("interest_facets") or []
    )
    sample["visibility"] = result.get("visibility") or "members"
    sample["synced_tag_keys"] = [key for key, _, _ in _tag_entries(result)]
    if result.get("persona"):
        sample["persona"] = result["persona"]
    if result.get("matching_hints"):
        sample["matching_hints"] = result["matching_hints"]
    profile.sample_summary = sample
    profile.model_version = result.get("model_version") or MODEL_VERSION
    profile.confirmed_at = now_utc()
    # Durable user tags: matching + member-visible chips read from Profile/TasteProfile.
    sync_taste_to_user_profile(db, session.user_id, result)
    result.setdefault("visibility", "members")
    return profile


def regenerate_ai_narrative(db: Session, user_id: str) -> dict[str, Any]:
    """Rebuild READY profile narrative with OpenCode DeepSeek V4 Flash.

    Reuses the latest completed Douyin import's collected items — no re-scan.
    If the user already answered refinement questions, re-apply them after the
    content baseline + AI polish step.
    """
    session = db.scalar(
        select(TasteImportSession)
        .where(
            TasteImportSession.user_id == user_id,
            TasteImportSession.source == SOURCE_DOUYIN,
            TasteImportSession.status == READY,
        )
        .order_by(TasteImportSession.completed_at.desc(), TasteImportSession.created_at.desc())
    )
    if session is None:
        raise AppError("TASTE_PROFILE_NOT_FOUND", "还没有可刷新的抖音画像，请先粘贴主页链接导入", 404)

    path = items_path(runtime_dir_for(session.id))
    if not path.is_file():
        raise AppError(
            "DOUYIN_LIKES_UNAVAILABLE",
            "本地喜欢内容已清理，请重新粘贴主页链接导入后再生成 AI 画像",
            409,
        )
    items: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not items:
        raise AppError("DOUYIN_LIKES_UNAVAILABLE", "没有可用于画像生成的喜欢内容", 409)

    api_pages = int((session.collection_summary or {}).get("api_pages") or 0)
    analysis = analyzer.analyze_content(items, api_pages=api_pages)
    questions = session.questions or analyzer.select_questions(analysis)
    session.questions = questions
    session.analysis_snapshot = {
        "item_count": analysis.item_count,
        "content_scores": analysis.content_scores,
        "dimensions": analysis.dimensions,
        "domain_shares": analysis.domain_shares,
        "recent200_domains": analysis.recent200_domains,
        "top_domains": analysis.top_domains,
        "sample_stats": analysis.sample_stats,
    }
    answer_list = [
        {"question_id": qid, "option_id": oid}
        for qid, oid in (session.answers or {}).items()
        if any(q.get("id") == qid for q in questions)
    ]
    if len(answer_list) >= MIN_ANSWERS:
        result = analyzer.score_answers(analysis, questions, answer_list)
        from onemore.modules.taste_profile.llm_enrich import enrich_provisional_profile

        result = enrich_provisional_profile(
            result,
            items,
            quiz_answers=answer_list,
            quiz_questions=questions,
        )
        result["calibrated"] = True
        if isinstance(result.get("sample"), dict):
            result["sample"]["calibrated"] = True
            result["sample"]["refined_with_quiz"] = True
    else:
        result = analyzer.build_provisional_result(analysis, items=items, use_llm=True)
    session.result_snapshot = result
    session.completed_at = now_utc()
    session.progress = {
        "phase": "ready",
        "current": analysis.item_count,
        "total": analysis.item_count,
        "percent": 100.0,
        "message": "已用 DeepSeek V4 Flash 刷新画像文案",
    }
    upsert_taste_profile(db, session, result)
    db.commit()
    db.refresh(session)
    return normalize_taste_result(result) or result


def get_taste_profile(db: Session, user_id: str) -> TasteProfile | None:
    return db.get(TasteProfile, user_id)


def persona_dict(db: Session, user_id: str) -> dict[str, Any] | None:
    """Full persona payload for competition / recruit scoring (no I/O besides DB)."""
    profile = get_taste_profile(db, user_id)
    if profile is None:
        return None
    sample = profile.sample_summary or {}
    return {
        "primary_tag": profile.primary_tag or {},
        "secondary_tags": profile.secondary_tags or [],
        "interest_domains": profile.interest_domains or [],
        "interest_facets": sample.get("interest_facets") or [],
        "matching_hints": sample.get("matching_hints") or [],
        "summary": profile.summary or "",
        "persona": sample.get("persona"),
    }


def taste_summary(db: Session, user_id: str) -> dict[str, Any] | None:
    """Compact card for /profile/me — enough for home + matching chips."""
    profile = get_taste_profile(db, user_id)
    if profile is None:
        return None
    sample = profile.sample_summary or {}
    secondary = profile.secondary_tags or []
    return {
        "status": READY,
        "primary_tag": profile.primary_tag,
        "secondary_tags": [
            tag.get("label") if isinstance(tag, dict) else tag for tag in secondary
        ],
        "interest_domains": [
            item.get("label") if isinstance(item, dict) else item
            for item in (profile.interest_domains or [])
        ],
        "interest_tags": public_interest_tags(db, user_id),
        "summary": profile.summary,
        "persona": sample.get("persona"),
        "matching_hints": sample.get("matching_hints") or [],
        "confidence": profile.confidence,
        "calibrated": bool(sample.get("calibrated", False)),
        "source": profile.source,
        "visibility": sample.get("visibility") or "members",
    }


def delete_taste(db: Session, user_id: str, orchestrator) -> dict[str, Any]:
    profile = db.get(TasteProfile, user_id)
    sessions = list(
        db.scalars(
            select(TasteImportSession).where(
                TasteImportSession.user_id == user_id,
                TasteImportSession.source == SOURCE_DOUYIN,
            )
        )
    )
    for session in sessions:
        orchestrator.cancel(session.id)
        remove_runtime_dir(session)
        db.delete(session)
    clear_taste_from_user_profile(db, user_id)
    if profile is not None:
        db.delete(profile)
    db.commit()
    return {"deleted_sessions": len(sessions), "deleted_profile": profile is not None}


def remove_runtime_dir(session: TasteImportSession | None = None, *, import_id: str | None = None) -> None:
    target_id = import_id or (session.id if session else None)
    if not target_id:
        return
    directory = runtime_dir_for(target_id)
    if directory.exists():
        shutil.rmtree(directory, ignore_errors=True)


def mark_interrupted_imports_failed(db: Session) -> int:
    active = db.scalars(
        select(TasteImportSession).where(TasteImportSession.status.not_in(TERMINAL_STATUSES))
    ).all()
    count = 0
    for session in active:
        session.status = FAILED
        session.error_code = "IMPORT_WORKER_RESTARTED"
        session.error_message = "服务重启导致后台任务中断，请重新导入"
        count += 1
    if count:
        db.commit()
    return count


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _collect_and_analyze_from_share_link(
    share_url: str,
    *,
    likes_limit: int | None = None,
    posts_limit: int | None = None,
    collects_limit: int | None = None,
    use_llm: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
    settings = get_settings()
    from onemore.modules.taste_profile.providers.douyin_http import DouyinHttpCollector

    likes_n = likes_limit if likes_limit is not None else settings.douyin_http_recent_likes
    posts_n = posts_limit if posts_limit is not None else settings.douyin_http_recent_posts
    collects_n = (
        collects_limit
        if collects_limit is not None
        else settings.douyin_http_recent_collects
    )
    collector = DouyinHttpCollector(
        timeout_seconds=settings.douyin_http_timeout_seconds,
    )
    bundle = collector.collect_recent(
        share_url,
        likes_limit=likes_n,
        posts_limit=posts_n,
        collects_limit=collects_n,
    )

    likes_items = [analyzer.normalize_item(raw) for raw in bundle["likes_raw"]]
    collect_items = [analyzer.normalize_item(raw) for raw in bundle["collects_raw"]]
    post_items = [analyzer.normalize_item(raw) for raw in bundle["posts_raw"]]
    like_ids = {str(x.get("aweme_id") or "") for x in likes_items if x.get("aweme_id")}
    collect_ids = {
        str(x.get("aweme_id") or "") for x in collect_items if x.get("aweme_id")
    }
    merged: dict[str, dict[str, Any]] = {}
    for item in likes_items + collect_items + post_items:
        aid = str(item.get("aweme_id") or "")
        if not aid or aid in merged:
            continue
        row = dict(item)
        if aid in like_ids:
            row["source_bucket"] = "like"
        elif aid in collect_ids:
            row["source_bucket"] = "collect"
        else:
            row["source_bucket"] = "post"
        merged[aid] = row
    items = list(merged.values())

    analysis = analyzer.analyze_content(
        items,
        api_pages=int(bundle["meta"]["likes"].get("pages") or 0)
        + int(bundle["meta"].get("collects", {}).get("pages") or 0)
        + int(bundle["meta"]["posts"].get("pages") or 0),
    )
    result = analyzer.build_provisional_result(analysis, items=items, use_llm=use_llm)
    result = normalize_taste_result(result) or result
    payload = {
        "share_url": share_url,
        "profile_url": bundle["profile_url"],
        "source_profile": bundle["source_profile"],
        "posts_count": len(post_items),
        "likes_count": len(likes_items),
        "collects_count": len(collect_items),
        "items_used": len(items),
        "collection": bundle["meta"],
        "result": result,
    }
    return payload, items, analysis


def analyze_from_share_link(
    share_url: str,
    *,
    likes_limit: int | None = None,
    posts_limit: int | None = None,
    collects_limit: int | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Sync HTTP path: share link → recent likes/collects/posts → taste result.

    No Playwright scrolling. Designed for ~30 recent likes + collects + posts.
    Does not persist to a user account.
    """
    payload, _items, _analysis = _collect_and_analyze_from_share_link(
        share_url,
        likes_limit=likes_limit,
        posts_limit=posts_limit,
        collects_limit=collects_limit,
        use_llm=use_llm,
    )
    return payload


def import_from_share_link(
    db: Session,
    user_id: str,
    share_url: str,
    *,
    likes_limit: int | None = None,
    posts_limit: int | None = None,
    collects_limit: int | None = None,
    use_llm: bool = True,
    force: bool = True,
    orchestrator=None,
) -> TasteImportSession:
    """Authenticated path: paste share link → persist READY session + taste profile."""
    settings = get_settings()
    if not settings.douyin_import_enabled:
        raise AppError("DOUYIN_IMPORT_DISABLED", "抖音兴趣导入功能未开启", 403)

    existing = _find_active_session(db, user_id)
    if existing is not None and not force:
        return existing
    if existing is not None:
        existing.status = CANCELLED
        existing.error_code = None
        existing.error_message = None
        if orchestrator is not None:
            orchestrator.cancel(existing.id)
        db.commit()

    payload, items, analysis = _collect_and_analyze_from_share_link(
        share_url,
        likes_limit=likes_limit,
        posts_limit=posts_limit,
        collects_limit=collects_limit,
        use_llm=use_llm,
    )
    result = payload["result"]
    from onemore.modules.taste_profile.taxonomy import TAG_DEFINITIONS

    labels = {tag.key: tag.label for tag in TAG_DEFINITIONS}
    candidate_tags = sorted(
        [
            {"key": key, "label": labels.get(key, key), "score": score}
            for key, score in analysis.content_scores.items()
        ],
        key=lambda item: item["score"],
        reverse=True,
    )
    questions = analyzer.select_questions(analysis)
    now = now_utc()
    session = TasteImportSession(
        id=f"imp_{new_id().replace('-', '')[:28]}",
        user_id=user_id,
        source=SOURCE_DOUYIN,
        status=READY,
        profile_url=payload["profile_url"],
        max_items=len(items),
        expires_at=now + timedelta(seconds=DEFAULT_TASK_TTL_SECONDS),
        authenticated_at=now,
        source_profile=payload.get("source_profile") or {},
        progress={
            "phase": "ready",
            "current": len(items),
            "total": len(items),
            "percent": 100.0,
            "message": "已根据喜欢和收藏生成画像，可选细化题进一步校准",
        },
        collection_summary={
            "api_pages": int((analysis.sample_stats or {}).get("api_pages") or 0),
            "items_collected": len(items),
            "has_more": False,
            "likes_count": payload["likes_count"],
            "collects_count": payload["collects_count"],
            "posts_count": payload["posts_count"],
            "collector": "http",
        },
        candidate_tags=candidate_tags,
        questions=questions,
        analysis_snapshot={
            "item_count": analysis.item_count,
            "content_scores": analysis.content_scores,
            "dimensions": analysis.dimensions,
            "domain_shares": analysis.domain_shares,
            "recent200_domains": analysis.recent200_domains,
            "top_domains": analysis.top_domains,
            "sample_stats": analysis.sample_stats,
        },
        result_snapshot=result,
        completed_at=now,
    )
    db.add(session)
    db.flush()

    runtime = runtime_dir_for(session.id)
    runtime.mkdir(parents=True, exist_ok=True)
    with items_path(runtime).open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    upsert_taste_profile(db, session, result)
    db.commit()
    db.refresh(session)
    return session
