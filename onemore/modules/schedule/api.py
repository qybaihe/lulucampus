from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onemore.core.auth import current_user, require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import Enrollment, User
from onemore.modules.schedule import service
from onemore.modules.schedule.schemas import (
    FreeWindowView,
    IntersectionRequest,
    IntersectionView,
    TimetableEntry,
    TimetableView,
)

router = APIRouter(tags=["schedule"])


def _refresh_background(user_id: str) -> None:
    from onemore.modules.schedule.orchestrator import refresh_user_timetable

    refresh_user_timetable(user_id)


@router.get("/schedule/timetable", response_model=APIResponse[TimetableView])
def get_timetable(
    week: int = Query(default=1, ge=1, le=30),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[TimetableView]:
    entries = [TimetableEntry(**item) for item in service.timetable_entries(db, user.id, week)]
    updated_at = db.scalar(
        select(func.max(Enrollment.updated_at)).where(Enrollment.user_id == user.id)
    )
    return APIResponse(
        data=TimetableView(week=week, entries=entries, updated_at=updated_at),
        meta={"private": True},
    )


@router.post(
    "/schedule/refresh",
    response_model=APIResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
)
def refresh_timetable(
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
) -> APIResponse[dict]:
    from onemore.core.config import get_settings

    if get_settings().is_production:
        from onemore.tasks.celery_app import celery_app

        celery_app.send_task("onemore.schedule.refresh_user", args=[user.id])
    else:
        background_tasks.add_task(_refresh_background, user.id)
    return APIResponse(data={"status": "accepted"}, meta={"poll": "/schedule/timetable"})


@router.get("/schedule/free-windows", response_model=APIResponse[list[FreeWindowView]])
def get_my_free_windows(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[list[FreeWindowView]]:
    return APIResponse(
        data=[FreeWindowView.model_validate(item) for item in service.get_free_windows(db, user.id)]
    )


@router.post(
    "/internal/schedule/intersections",
    response_model=APIResponse[list[IntersectionView]],
    dependencies=[Depends(require_admin)],
)
def internal_intersections(
    body: IntersectionRequest, db: Session = Depends(get_db)
) -> APIResponse[list[IntersectionView]]:
    return APIResponse(
        data=service.intersect_windows(
            db,
            body.user_ids,
            start_after=body.start_after,
            end_before=body.end_before,
            minimum_minutes=body.minimum_minutes,
        )
    )
