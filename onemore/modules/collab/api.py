from __future__ import annotations

import base64
from datetime import datetime

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user, user_id_from_credentials, user_id_from_token
from onemore.core.database import SessionLocal, get_db
from onemore.core.errors import AppError
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.collab import service
from onemore.modules.collab.realtime import hub
from onemore.modules.collab.schemas import (
    ChannelScenePolicyView,
    MentionAzouRequest,
    MentionAzouResult,
    MessageCreate,
    MessageView,
    RecurRelationRequest,
    RelationView,
    SharedGoalCreate,
    SharedGoalUpdate,
    SharedGoalView,
)
from onemore.modules.gathering import service as gathering_service
from onemore.modules.cast_driver.reactive_chat import (
    catch_up_if_needed,
    schedule_cast_replies,
    should_schedule,
)

router = APIRouter(tags=["collab"])


def _message_view(message, db=None) -> MessageView:
    return MessageView.model_validate(service.message_view_data(message, db=db))


async def _broadcast_authorized(channel_id: str, payload: dict) -> None:
    with SessionLocal() as db:
        allowed = service.authorized_channel_user_ids(db, channel_id)
    await hub.broadcast(channel_id, payload, allowed_user_ids=allowed)


@router.get("/channels/{channel_id}/messages", response_model=APIResponse[list[MessageView]])
async def channel_messages(
    channel_id: str,
    before: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[MessageView]]:
    items = service.list_messages(db, channel_id, user.id, before=before, limit=limit)
    catch_up_if_needed(channel_id)
    return APIResponse(data=[_message_view(item, db) for item in items])


@router.get(
    "/channels/{channel_id}/scene-policy",
    response_model=APIResponse[ChannelScenePolicyView],
)
def channel_scene_policy(
    channel_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ChannelScenePolicyView]:
    return APIResponse(
        data=ChannelScenePolicyView.model_validate(
            service.channel_scene_policy(db, channel_id, user.id)
        )
    )


@router.post(
    "/channels/{channel_id}/messages",
    response_model=APIResponse[MessageView],
    status_code=status.HTTP_201_CREATED,
)
async def post_channel_message(
    channel_id: str,
    body: MessageCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[MessageView]:
    content = service.prepare_message_content(db, channel_id, user.id, body)
    message = service.send_message(db, channel_id, user.id, content, body.content_type)
    view = _message_view(message, db)
    await _broadcast_authorized(channel_id, view.model_dump(mode="json"))
    if should_schedule(user.id, body.content_type):
        schedule_cast_replies(channel_id, message.id, user.id)
    return APIResponse(data=view)


@router.post(
    "/channels/{channel_id}/mention-azou",
    response_model=APIResponse[MentionAzouResult],
)
async def mention_azou(
    channel_id: str,
    body: MentionAzouRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[MentionAzouResult]:
    message, hint = service.mention_azou(db, channel_id, user.id, body.text)
    view = _message_view(message, db)
    await _broadcast_authorized(channel_id, view.model_dump(mode="json"))
    return APIResponse(data=MentionAzouResult(message=view, action_hint=hint))


_WS_SUBPROTOCOL = "onemore.v1"
_WS_AUTH_PREFIX = "om-auth."


def _websocket_credentials(websocket: WebSocket) -> tuple[str | None, str | None]:
    """Resolve (user_id, accept_subprotocol) for a channel socket.

    Native clients keep sending Authorization / X-User-ID headers. Browsers
    cannot set custom WebSocket headers, so they may offer the token inside
    the Sec-WebSocket-Protocol list as `om-auth.<base64url(token)>` alongside
    `onemore.v1` — this keeps raw tokens out of URLs.
    """

    user_id = user_id_from_credentials(
        websocket.headers.get("authorization"), websocket.headers.get("x-user-id")
    )
    offered = [
        item.strip()
        for item in (websocket.headers.get("sec-websocket-protocol") or "").split(",")
        if item.strip()
    ]
    subprotocol = _WS_SUBPROTOCOL if _WS_SUBPROTOCOL in offered else None
    if user_id is None:
        for item in offered:
            if not item.startswith(_WS_AUTH_PREFIX):
                continue
            encoded = item[len(_WS_AUTH_PREFIX) :]
            try:
                token = base64.urlsafe_b64decode(
                    encoded + "=" * (-len(encoded) % 4)
                ).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                continue
            user_id = user_id_from_token(token)
            if user_id:
                break
    return user_id, subprotocol


@router.websocket("/channels/{channel_id}")
async def channel_socket(websocket: WebSocket, channel_id: str):
    user_id, subprotocol = _websocket_credentials(websocket)
    if user_id is None:
        await websocket.close(code=4401)
        return
    with SessionLocal() as db:
        try:
            service.require_channel_live_access(db, channel_id, user_id)
        except AppError:
            await websocket.close(code=4403)
            return
    await hub.connect(channel_id, user_id, websocket, subprotocol=subprotocol)
    try:
        while True:
            payload = await websocket.receive_json()
            body = MessageCreate.model_validate(payload)
            try:
                with SessionLocal() as db:
                    service.require_channel_live_access(db, channel_id, user_id)
                    content = service.prepare_message_content(db, channel_id, user_id, body)
                    message = service.send_message(
                        db, channel_id, user_id, content, body.content_type
                    )
                    view = _message_view(message, db)
            except AppError:
                await websocket.close(code=4403)
                break
            await _broadcast_authorized(channel_id, view.model_dump(mode="json"))
            if should_schedule(user_id, body.content_type):
                schedule_cast_replies(channel_id, view.id, user_id)
    except WebSocketDisconnect:
        hub.disconnect(channel_id, websocket)


@router.get("/relations", response_model=APIResponse[list[RelationView]])
def my_relations(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[list[RelationView]]:
    return APIResponse(
        data=[RelationView.model_validate(item) for item in service.list_relations(db, user.id)]
    )


@router.get("/relations/{relation_id}", response_model=APIResponse[RelationView])
def relation_detail(
    relation_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[RelationView]:
    return APIResponse(
        data=RelationView.model_validate(service.get_relation(db, relation_id, user.id))
    )


@router.post("/relations/{relation_id}/recur", response_model=APIResponse[dict])
def recur_relation(
    relation_id: str,
    body: RecurRelationRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    relation = service.get_relation(db, relation_id, user.id)
    latest = relation["experiences"][0] if relation["experiences"] else None
    if latest is None:
        raise AppError("NO_SHARED_EXPERIENCE", "当前关系没有可复用的共同经历", 409)
    clone = gathering_service.recur(db, latest.gathering_id, user.id, None)
    if body.gathering_type:
        clone.gathering_type = body.gathering_type
        db.commit()
    return APIResponse(data={"gathering_id": clone.id, "status": clone.status})


@router.delete("/relations/{relation_id}", response_model=APIResponse[dict])
def dissolve_relation(
    relation_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    service.dissolve_relation(db, relation_id, user.id)
    return APIResponse(data={"id": relation_id, "status": "dissolved", "notified": False})


@router.post(
    "/relations/{relation_id}/goals",
    response_model=APIResponse[SharedGoalView],
    status_code=status.HTTP_201_CREATED,
)
def create_shared_goal(
    relation_id: str,
    body: SharedGoalCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[SharedGoalView]:
    goal = service.create_goal(
        db,
        relation_id,
        user.id,
        definition=body.definition,
        period_start=body.period_start,
        period_end=body.period_end,
        target_value=body.target_value,
        unit=body.unit,
    )
    return APIResponse(
        data=SharedGoalView.model_validate(service.shared_goal_view(db, goal))
    )


@router.get(
    "/relations/{relation_id}/goals",
    response_model=APIResponse[list[SharedGoalView]],
)
def list_shared_goals(
    relation_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[SharedGoalView]]:
    return APIResponse(
        data=[
            SharedGoalView.model_validate(service.shared_goal_view(db, item))
            for item in service.list_goals(db, relation_id, user.id)
        ]
    )


@router.get("/goals/{goal_id}", response_model=APIResponse[SharedGoalView])
def shared_goal_detail(
    goal_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[SharedGoalView]:
    goal = service.get_goal(db, goal_id, user.id)
    return APIResponse(
        data=SharedGoalView.model_validate(service.shared_goal_view(db, goal))
    )


@router.patch("/goals/{goal_id}", response_model=APIResponse[SharedGoalView])
def update_shared_goal(
    goal_id: str,
    body: SharedGoalUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[SharedGoalView]:
    goal = service.update_goal_next_action(db, goal_id, user.id, body.next_action)
    return APIResponse(
        data=SharedGoalView.model_validate(service.shared_goal_view(db, goal))
    )
