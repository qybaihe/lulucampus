from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.hermes.schemas import ActionName
from onemore.modules.actions import service as action_service
from onemore.modules.campus import service
from onemore.modules.campus.schemas import (
    CampusEventCreateRequest,
    HermesAskRequest,
    HermesAskResult,
    HermesPeerChatResult,
    HermesPeerStartRequest,
    PublicEventView,
    SceneTriggerIgnore,
)

router = APIRouter(tags=["campus-tools"])


@router.get("/today/summary", response_model=APIResponse[dict])
def today_summary(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[dict]:
    return APIResponse(data=service.today_summary(db, user))


@router.post("/today/triggers/{scene_key}/ignore", response_model=APIResponse[dict])
def ignore_trigger(
    scene_key: str,
    body: SceneTriggerIgnore,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    return APIResponse(data=service.ignore_scene_trigger(db, user.id, scene_key))


@router.get("/assignments", response_model=APIResponse[list[dict]])
def assignments(
    status: str = Query(default="unfinished"),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[dict]]:
    return APIResponse(data=service.list_assignments(db, user.id, status))


@router.get("/assignments/{assignment_id}", response_model=APIResponse[dict])
def assignment_detail(
    assignment_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    return APIResponse(data=service.assignment_detail(db, user.id, assignment_id))


@router.get("/schedule/courses/{course_id}", response_model=APIResponse[dict])
def course_detail(
    course_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    return APIResponse(data=service.course_detail(db, user.id, course_id))


@router.get("/venues/room/available", response_model=APIResponse[dict])
def room_availability(
    kind: str = Query(),
    day: date = Query(alias="date"),
    lab: str | None = Query(default=None),
    room: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    data = action_service.execute_read_action(
        db,
        user.id,
        ActionName.ROOM_AVAILABLE,
        {"kind": kind, "date": day, "lab": lab, "room": room},
    )
    return APIResponse(data=data)


@router.get("/venues/gym/available", response_model=APIResponse[dict])
def gym_availability(
    venue_type: str = Query(),
    day: date | None = Query(default=None, alias="date"),
    days: int = Query(default=1, ge=1, le=7),
    venue: str | None = Query(default=None),
    include_full: bool = Query(default=False),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    data = action_service.execute_read_action(
        db,
        user.id,
        ActionName.GYM_AVAILABLE,
        {
            "venue_type": venue_type,
            "date": day,
            "days": days,
            "venue": venue,
            "include_full": include_full,
        },
    )
    return APIResponse(data=data)


@router.get("/events", response_model=APIResponse[list[PublicEventView]])
def public_events(
    event_type: str | None = Query(default=None, alias="type"),
    start: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> APIResponse[list[PublicEventView]]:
    return APIResponse(data=service.list_events(db, event_type, start))


@router.get("/events/{event_id}", response_model=APIResponse[PublicEventView])
def public_event_detail(
    event_id: str, db: Session = Depends(get_db)
) -> APIResponse[PublicEventView]:
    return APIResponse(data=service.event_detail(db, event_id))


@router.post("/events", response_model=APIResponse[PublicEventView], status_code=201)
def publish_event(
    body: CampusEventCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[PublicEventView]:
    return APIResponse(data=service.create_user_event(db, user.id, body))


@router.post("/hermes/ask", response_model=APIResponse[HermesAskResult])
def ask_hermes(
    body: HermesAskRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[HermesAskResult]:
    return APIResponse(
        data=HermesAskResult.model_validate(
            service.hermes_ask(db, user.id, body.text, body.context)
        )
    )


@router.post("/hermes/peers/start", response_model=APIResponse[HermesPeerChatResult])
def start_hermes_peer_chat(
    body: HermesPeerStartRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[HermesPeerChatResult]:
    from onemore.modules.campus.peers import start_peer_chat

    return APIResponse(
        data=HermesPeerChatResult.model_validate(
            start_peer_chat(
                db,
                user,
                body.peer_user_id,
                reason=body.reason,
                overlap=body.overlap,
            )
        )
    )
