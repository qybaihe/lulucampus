from __future__ import annotations

import base64
import time
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.config import get_settings
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import TasteImportSession, User
from onemore.modules.taste_profile import service
from onemore.modules.taste_profile.orchestrator import taste_orchestrator
from onemore.modules.taste_profile.schemas import (
    DemoTasteFromLinkRequest,
    ImportCreateRequest,
    ImportItemView,
    ImportSessionView,
    ItemsPageView,
    LoginVerificationView,
    PhoneCodeRequest,
    PhoneCodeSubmit,
    PhoneLoginView,
    QRLoginView,
    QuestionsView,
    QuizAnswersRequest,
    TasteProfileResultView,
)

router = APIRouter(tags=["taste_profile"])


def _result_data(result: dict[str, Any]) -> dict[str, Any]:
    normalized = service.normalize_taste_result(result)
    return normalized or {"status": service.READY, **result}


def _mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "*" * len(phone)
    if len(phone) > 8:
        return f"{phone[:3]}{'*' * (len(phone) - 7)}{phone[-4:]}"
    return f"{phone[:2]}{'*' * (len(phone) - 4)}{phone[-2:]}"


def _qr_image_path(session: TasteImportSession) -> str:
    return f"/profile/imports/{session.id}/qr/image?v={session.qr_version}"


def _wait_for_status(
    db: Session,
    import_id: str,
    user_id: str,
    *,
    wait_seconds: int,
    predicate: Callable[[TasteImportSession], bool],
) -> TasteImportSession:
    deadline = time.monotonic() + wait_seconds
    while True:
        db.expire_all()
        session = service.get_import(db, import_id, user_id)
        if predicate(session) or time.monotonic() >= deadline:
            return session
        time.sleep(0.2)


@router.post(
    "/profile/imports/douyin",
    response_model=APIResponse[ImportSessionView],
    status_code=status.HTTP_202_ACCEPTED,
)
def create_import(
    body: ImportCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ImportSessionView]:
    settings = get_settings()
    if not settings.douyin_import_enabled:
        from onemore.core.errors import AppError

        raise AppError("DOUYIN_IMPORT_DISABLED", "抖音兴趣导入功能未开启", 403)
    session = service.create_import(
        db,
        user.id,
        profile_url=body.profile_url,
        max_items=body.max_items,
        force=body.force,
        orchestrator=taste_orchestrator,
    )
    if session.status == service.PREPARING_QR:
        taste_orchestrator.submit(session.id)
    return APIResponse(
        data=ImportSessionView.model_validate(service.to_view(session)),
        meta={
            "login_methods": ["qr_then_phone"],
            "qr": f"/profile/imports/{session.id}/qr",
            "phone_code": f"/profile/imports/{session.id}/phone/code",
            "verify": f"/profile/imports/{session.id}/verify",
            "poll": f"/profile/imports/{session.id}",
            "poll_after_seconds": 2,
        },
    )


@router.post(
    "/profile/imports/douyin/qr",
    response_model=APIResponse[QRLoginView],
    status_code=status.HTTP_202_ACCEPTED,
)
def create_login_qr(
    body: ImportCreateRequest,
    wait_seconds: int = Query(default=10, ge=0, le=15),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[QRLoginView]:
    session = service.create_import(
        db,
        user.id,
        profile_url=body.profile_url,
        max_items=body.max_items,
        force=body.force,
        orchestrator=taste_orchestrator,
    )
    if session.status == service.PREPARING_QR:
        taste_orchestrator.submit(session.id)
    session = _wait_for_status(
        db,
        session.id,
        user.id,
        wait_seconds=wait_seconds,
        predicate=lambda current: bool(current.qr_image_data_url)
        or current.status in service.TERMINAL_STATUSES,
    )
    view = service.to_view(session)
    return APIResponse(
        data=QRLoginView(
            import_id=session.id,
            status=session.status,
            qr_image_data_url=view["qr_image_data_url"],
            qr_version=session.qr_version,
            qr_expires_at=view["qr_expires_at"],
            qr_image_url=_qr_image_path(session),
            phone_code=f"/profile/imports/{session.id}/phone/code",
            verify=f"/profile/imports/{session.id}/verify",
            error=view["error"],
        ),
        meta={"poll_after_seconds": 2},
    )


@router.get("/profile/imports/{import_id}", response_model=APIResponse[ImportSessionView])
def get_import(
    import_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ImportSessionView]:
    session = service.get_import(db, import_id, user.id)
    view = service.to_view(session)
    meta: dict[str, Any] = {"poll_after_seconds": 2}
    meta["can_refresh_qr"] = session.status in {service.WAITING_SCAN, service.QR_EXPIRED}
    meta["can_cancel"] = session.status not in service.TERMINAL_STATUSES
    return APIResponse(data=ImportSessionView.model_validate(view), meta=meta)


@router.get(
    "/profile/imports/{import_id}/qr",
    response_model=APIResponse[QRLoginView],
)
def get_login_qr(
    import_id: str,
    wait_seconds: int = Query(default=0, ge=0, le=15),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[QRLoginView]:
    session = _wait_for_status(
        db,
        import_id,
        user.id,
        wait_seconds=wait_seconds,
        predicate=lambda current: bool(current.qr_image_data_url)
        or current.status in service.TERMINAL_STATUSES,
    )
    view = service.to_view(session)
    return APIResponse(
        data=QRLoginView(
            import_id=session.id,
            status=session.status,
            qr_image_data_url=view["qr_image_data_url"],
            qr_version=session.qr_version,
            qr_expires_at=view["qr_expires_at"],
            qr_image_url=_qr_image_path(session),
            phone_code=f"/profile/imports/{session.id}/phone/code",
            verify=f"/profile/imports/{session.id}/verify",
            error=view["error"],
        ),
        meta={"poll_after_seconds": 2},
    )


@router.get(
    "/profile/imports/{import_id}/qr/image",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
def get_login_qr_image(
    import_id: str,
    v: int | None = Query(default=None, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    from onemore.core.errors import AppError

    session = service.get_import(db, import_id, user.id)
    if v is not None and v != session.qr_version:
        raise AppError("DOUYIN_QR_VERSION_STALE", "二维码版本已过期，请重新获取", 409)
    data_url = session.qr_image_data_url or ""
    if not data_url.startswith("data:image/png;base64,"):
        raise AppError("DOUYIN_QR_NOT_FOUND", "二维码尚未生成或已经清理", 409)
    try:
        image = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except ValueError as exc:
        raise AppError("DOUYIN_QR_NOT_FOUND", "二维码数据不可用", 409) from exc
    return Response(
        content=image,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.post(
    "/profile/imports/{import_id}/verify",
    response_model=APIResponse[LoginVerificationView],
)
def verify_mobile_login(
    import_id: str,
    wait_seconds: int = Query(default=0, ge=0, le=15),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[LoginVerificationView]:
    pre_auth = {service.PREPARING_QR, service.WAITING_SCAN, service.QR_EXPIRED}
    session = _wait_for_status(
        db,
        import_id,
        user.id,
        wait_seconds=wait_seconds,
        predicate=lambda current: current.status not in pre_auth,
    )
    verified = session.authenticated_at is not None
    view = service.to_view(session)
    return APIResponse(
        data=LoginVerificationView(
            import_id=session.id,
            status=session.status,
            verified=verified,
            authenticated_at=session.authenticated_at,
            source_profile=view["source_profile"],
            next=f"/profile/imports/{session.id}",
            error=view["error"],
        ),
        meta={"poll_after_seconds": 2},
    )


@router.post(
    "/profile/imports/{import_id}/phone/code",
    response_model=APIResponse[PhoneLoginView],
)
def request_phone_code(
    import_id: str,
    body: PhoneCodeRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[PhoneLoginView]:
    session = service.get_import(db, import_id, user.id)
    if session.status not in {service.QR_SCANNED, service.PHONE_REQUIRED}:
        from onemore.core.errors import AppError

        raise AppError("DOUYIN_SCAN_REQUIRED", "请先完成抖音二维码扫码", 409)
    phone = body.phone.get_secret_value()
    try:
        taste_orchestrator.request_sms_code(import_id, phone, body.country_code)
    finally:
        phone_masked = _mask_phone(phone)
        phone = ""
    session = service.mark_phone_code_sent(db, import_id, user.id, phone_masked)
    return APIResponse(
        data=PhoneLoginView(
            import_id=session.id,
            status=session.status,
            phone_masked=phone_masked,
            code_sent=True,
            submit_code=f"/profile/imports/{session.id}/phone/verify",
            verify=f"/profile/imports/{session.id}/verify",
        ),
        meta={"code_ttl_seconds": 300, "poll_after_seconds": 2},
    )


@router.get(
    "/profile/imports/{import_id}/phone",
    response_model=APIResponse[PhoneLoginView],
)
def get_phone_login_status(
    import_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[PhoneLoginView]:
    session = service.get_import(db, import_id, user.id)
    phone = service.phone_login_view(session)
    return APIResponse(
        data=PhoneLoginView(
            import_id=session.id,
            status=session.status,
            phone_masked=phone["phone_masked"],
            code_sent=phone["code_sent"],
            verified=session.authenticated_at is not None,
            authenticated_at=session.authenticated_at,
            submit_code=f"/profile/imports/{session.id}/phone/verify",
            verify=f"/profile/imports/{session.id}/verify",
            error=service.to_view(session)["error"],
        ),
        meta={"poll_after_seconds": 2},
    )


@router.post(
    "/profile/imports/{import_id}/phone/verify",
    response_model=APIResponse[PhoneLoginView],
)
def submit_phone_code(
    import_id: str,
    body: PhoneCodeSubmit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[PhoneLoginView]:
    session = service.get_import(db, import_id, user.id)
    code = body.code.get_secret_value()
    try:
        taste_orchestrator.submit_sms_code(import_id, code)
    finally:
        code = ""
    session = _wait_for_status(
        db,
        import_id,
        user.id,
        wait_seconds=5,
        predicate=lambda current: current.authenticated_at is not None
        or current.status in service.TERMINAL_STATUSES,
    )
    return APIResponse(
        data=PhoneLoginView(
            import_id=session.id,
            status=session.status,
            code_sent=True,
            verified=session.authenticated_at is not None,
            authenticated_at=session.authenticated_at,
            submit_code=f"/profile/imports/{session.id}/phone/verify",
            verify=f"/profile/imports/{session.id}/verify",
            error=service.to_view(session)["error"],
        ),
        meta={"poll_after_seconds": 2},
    )


@router.post(
    "/profile/imports/{import_id}/qr/refresh",
    response_model=APIResponse[ImportSessionView],
    status_code=status.HTTP_202_ACCEPTED,
)
def refresh_qr(
    import_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ImportSessionView]:
    session = service.request_qr_refresh(db, import_id, user.id, taste_orchestrator)
    return APIResponse(
        data=ImportSessionView.model_validate(service.to_view(session)),
        meta={"poll_after_seconds": 2},
    )


@router.post("/profile/imports/{import_id}/cancel", response_model=APIResponse[ImportSessionView])
def cancel_import(
    import_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ImportSessionView]:
    session = service.cancel_import(db, import_id, user.id, taste_orchestrator)
    return APIResponse(data=ImportSessionView.model_validate(service.to_view(session)))


@router.get("/profile/imports/{import_id}/items", response_model=APIResponse[ItemsPageView])
def list_items(
    import_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> APIResponse[ItemsPageView]:
    page = service.get_items(db, import_id, user.id, cursor=cursor, limit=limit)
    items = [ImportItemView.model_validate(item) for item in page["items"]]
    return APIResponse(
        data=ItemsPageView(
            items=items,
            next_cursor=page["next_cursor"],
            has_more=page["has_more"],
        )
    )


@router.get("/profile/imports/{import_id}/questions", response_model=APIResponse[QuestionsView])
def get_questions(
    import_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[QuestionsView]:
    payload = service.get_questions(db, import_id, user.id)
    return APIResponse(
        data=QuestionsView(**payload),
        meta={
            "min_answers": payload.get("min_answers", 3),
            "max_questions": payload.get("max_answers", 5),
            "schema_version": payload.get("schema_version", "taste-quiz-v1"),
        },
    )


@router.post(
    "/profile/imports/{import_id}/answers",
    response_model=APIResponse[TasteProfileResultView],
)
def submit_answers(
    import_id: str,
    body: QuizAnswersRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TasteProfileResultView]:
    """iOS posts quiz JSON answers → rule refine + AI re-narrate."""
    answers = [item.model_dump() for item in body.answers]
    result = service.submit_answers(db, import_id, user.id, answers)
    return APIResponse(
        data=TasteProfileResultView.model_validate(_result_data(result)),
        meta={"refined_with_quiz": True, "ai_rewritten": True},
    )


@router.post(
    "/profile/taste/from-link",
    response_model=APIResponse[ImportSessionView],
)
def taste_from_link(
    body: DemoTasteFromLinkRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ImportSessionView]:
    """Paste a Douyin homepage share link → likes + collects + posts → persist profile."""
    settings = get_settings()
    if not settings.douyin_import_enabled:
        from onemore.core.errors import AppError

        raise AppError("DOUYIN_IMPORT_DISABLED", "抖音兴趣导入功能未开启", 403)
    session = service.import_from_share_link(
        db,
        user.id,
        body.share_url,
        likes_limit=body.likes_limit,
        posts_limit=body.posts_limit,
        collects_limit=body.collects_limit,
        use_llm=body.use_llm,
        force=body.force,
        orchestrator=taste_orchestrator,
    )
    return APIResponse(
        data=ImportSessionView.model_validate(service.to_view(session)),
        meta={
            "collector": "http",
            "note": "默认约 30 条最近喜欢 + 30 条收藏 + 若干作品；喜欢和收藏里的视频需公开",
        },
    )


@router.get(
    "/profile/taste/me",
    response_model=APIResponse[TasteProfileResultView | None],
)
def get_my_taste(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TasteProfileResultView | None]:
    profile = service.get_taste_profile(db, user.id)
    if profile is None:
        return APIResponse(data=None)
    return APIResponse(
        data=TasteProfileResultView.model_validate(_result_data(_profile_result(profile)))
    )


@router.post(
    "/profile/taste/me/ai-refresh",
    response_model=APIResponse[TasteProfileResultView],
)
def refresh_my_taste_ai(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TasteProfileResultView]:
    """Re-generate persona narrative with OpenCode Go · DeepSeek V4 Flash.

    Does not re-scan Douyin; reuses the latest READY import's collected likes.
    """
    result = service.regenerate_ai_narrative(db, user.id)
    return APIResponse(
        data=TasteProfileResultView.model_validate(_result_data(result)),
        meta={
            "llm_provider": "opencode-go",
            "llm_model": "deepseek-v4-flash",
            "endpoint": "https://opencode.ai/zen/go/v1/chat/completions",
        },
    )


@router.delete("/profile/taste/me/douyin", response_model=APIResponse[dict[str, Any]])
def delete_my_douyin_taste(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict[str, Any]]:
    payload = service.delete_taste(db, user.id, taste_orchestrator)
    return APIResponse(data=payload)


def _profile_result(profile) -> dict[str, Any]:
    sample = profile.sample_summary or {}
    return {
        "primary_tag": profile.primary_tag,
        "secondary_tags": profile.secondary_tags,
        "interest_domains": profile.interest_domains,
        "dimensions": profile.dimensions,
        "summary": profile.summary,
        "confidence": profile.confidence,
        "sample": sample,
        "interest_facets": sample.get("interest_facets") or [],
        "persona": sample.get("persona"),
        "matching_hints": sample.get("matching_hints") or [],
        "calibrated": bool(sample.get("calibrated", False)),
        "calibrated_at": sample.get("calibrated_at"),
        "source": profile.source,
        "model_version": profile.model_version,
        "visibility": (profile.sample_summary or {}).get("visibility") or "members",
    }
