"""Public judge/demo entry for Douyin taste import — no App login required.

Each browser visit mints an ephemeral guest user + access token, then reuses
the normal taste_profile import/poll endpoints with that Bearer token.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from onemore.core.auth import issue_access_token
from onemore.core.config import get_settings
from onemore.core.database import get_db
from onemore.core.errors import AppError
from onemore.core.schemas import APIResponse
from onemore.db.models import User, new_id
from onemore.modules.taste_profile import service
from onemore.modules.taste_profile.orchestrator import taste_orchestrator
from onemore.modules.taste_profile.providers.douyin_http import http_cookie_ready
from onemore.modules.taste_profile.schemas import (
    DemoTasteFromLinkRequest,
    DemoTasteFromLinkView,
    DemoTasteStartView,
    DemoTasteStatusView,
    ImportCreateRequest,
    TasteProfileResultView,
)

router = APIRouter(tags=["demo_taste"])


def _require_demo_enabled() -> None:
    settings = get_settings()
    if not settings.demo_taste_public_enabled:
        raise AppError("DEMO_TASTE_DISABLED", "评委体验入口未开启", 403)
    if not settings.douyin_import_enabled:
        raise AppError("DOUYIN_IMPORT_DISABLED", "抖音兴趣导入功能未开启", 403)


def _create_guest_user(db: Session) -> User:
    suffix = new_id().replace("-", "")[:20]
    user = User(
        id=f"guest_{suffix}",
        display_name="评委体验",
        account_status="active",
        social_enabled=False,
        course_matching_enabled=False,
        calendar_enabled=False,
        notification_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _qr_image_path(session) -> str:
    return f"/profile/imports/{session.id}/qr/image?v={session.qr_version}"


def _wait_for_status(
    db: Session,
    import_id: str,
    user_id: str,
    *,
    wait_seconds: int,
    predicate: Callable,
):
    deadline = time.monotonic() + wait_seconds
    while True:
        db.expire_all()
        session = service.get_import(db, import_id, user_id)
        if predicate(session) or time.monotonic() >= deadline:
            return session
        time.sleep(0.2)


@router.get("/demo/taste/status", response_model=APIResponse[DemoTasteStatusView])
def demo_taste_status() -> APIResponse[DemoTasteStatusView]:
    settings = get_settings()
    enabled = settings.demo_taste_public_enabled and settings.douyin_import_enabled
    http_ready = http_cookie_ready()
    if not settings.demo_taste_public_enabled:
        message = "评委体验入口未开启"
    elif not settings.douyin_import_enabled:
        message = "抖音兴趣导入功能未开启"
    elif http_ready:
        message = "支持分享链接导入（最近喜欢 + 收藏 + 作品，无需扫码）"
    elif settings.douyin_mode == "fake":
        message = "本地假扫码演示模式（可完整走通画像生成）"
    else:
        message = "真实抖音扫码模式：打开抖音扫一扫即可体验"
    return APIResponse(
        data=DemoTasteStatusView(
            enabled=enabled,
            douyin_import_enabled=settings.douyin_import_enabled,
            mode=settings.douyin_mode,
            message=message,
            http_link_import_ready=http_ready,
        )
    )


@router.post(
    "/demo/taste/from-link",
    response_model=APIResponse[DemoTasteFromLinkView],
)
def demo_taste_from_link(
    body: DemoTasteFromLinkRequest,
) -> APIResponse[DemoTasteFromLinkView]:
    """Public sync import: Douyin share link → recent likes/collects/posts → persona.

    Uses local operator cookies over HTTP. No Playwright page scrolling.
    Requires the target account's 喜欢 and 收藏 videos to be public.
    """
    _require_demo_enabled()
    payload = service.analyze_from_share_link(
        body.share_url,
        likes_limit=body.likes_limit,
        posts_limit=body.posts_limit,
        collects_limit=body.collects_limit,
        use_llm=body.use_llm,
    )
    result = payload["result"]
    try:
        result_view: TasteProfileResultView | dict = TasteProfileResultView.model_validate(
            result
        )
    except Exception:
        result_view = result
    return APIResponse(
        data=DemoTasteFromLinkView(
            source="douyin_http_link",
            share_url=payload["share_url"],
            profile_url=payload["profile_url"],
            source_profile=payload.get("source_profile"),
            posts_count=payload["posts_count"],
            likes_count=payload["likes_count"],
            collects_count=payload.get("collects_count") or 0,
            items_used=payload["items_used"],
            collection=payload["collection"],
            result=result_view,
        ),
        meta={
            "collector": "http",
            "note": "默认约 30 条最近喜欢 + 30 条收藏 + 若干作品；喜欢和收藏里的视频需公开",
        },
    )


@router.post(
    "/demo/taste/douyin/qr",
    response_model=APIResponse[DemoTasteStartView],
    status_code=status.HTTP_202_ACCEPTED,
)
def start_demo_taste_qr(
    body: ImportCreateRequest,
    wait_seconds: int = Query(default=10, ge=0, le=15),
    db: Session = Depends(get_db),
) -> APIResponse[DemoTasteStartView]:
    """Mint a guest identity and start Douyin QR login — no prior App auth."""
    _require_demo_enabled()
    settings = get_settings()
    guest = _create_guest_user(db)
    token = issue_access_token(guest.id)
    session = service.create_import(
        db,
        guest.id,
        profile_url=body.profile_url,
        max_items=body.max_items,
        force=True,
        orchestrator=taste_orchestrator,
    )
    if session.status == service.PREPARING_QR:
        taste_orchestrator.submit(session.id)
    session = _wait_for_status(
        db,
        session.id,
        guest.id,
        wait_seconds=wait_seconds,
        predicate=lambda current: bool(current.qr_image_data_url)
        or current.status in service.TERMINAL_STATUSES,
    )
    view = service.to_view(session)
    return APIResponse(
        data=DemoTasteStartView(
            access_token=token,
            guest_user_id=guest.id,
            mode=settings.douyin_mode,
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
        meta={
            "poll_after_seconds": 2,
            "poll": f"/profile/imports/{session.id}",
            "auth": "Bearer <access_token>",
            "note": "后续轮询/验证/画像请携带返回的 access_token，无需 App 登录",
        },
    )
