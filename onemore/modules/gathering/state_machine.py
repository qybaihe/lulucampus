from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from sqlalchemy.orm import Session

from onemore.core.errors import ConflictError
from onemore.db.models import Gathering, GatheringStatus, GatheringTransition, utcnow


class GatheringEvent(StrEnum):
    PUBLISH = "publish"
    MATCHED = "matched"
    MEMBER_LEFT = "member_left"
    ALL_CONFIRMED = "all_confirmed"
    PREVIEW_CREATED = "preview_created"
    ACTION_SUCCEEDED = "action_succeeded"
    ACTION_FAILED = "action_failed"
    PREVIEW_INVALIDATED = "preview_invalidated"
    START = "start"
    COMPLETE = "complete"
    RECUR = "recur"
    ARCHIVE = "archive"
    DISSOLVE = "dissolve"
    RESCHEDULE = "reschedule"
    ROLLBACK = "rollback"


TRANSITIONS: dict[tuple[str, GatheringEvent], str] = {
    (GatheringStatus.DRAFT.value, GatheringEvent.PUBLISH): GatheringStatus.POOLING.value,
    (GatheringStatus.POOLING.value, GatheringEvent.MATCHED): GatheringStatus.TENTATIVE.value,
    (GatheringStatus.TENTATIVE.value, GatheringEvent.MEMBER_LEFT): GatheringStatus.POOLING.value,
    (GatheringStatus.CONFIRMED.value, GatheringEvent.MEMBER_LEFT): GatheringStatus.POOLING.value,
    (GatheringStatus.PREVIEWED.value, GatheringEvent.MEMBER_LEFT): GatheringStatus.POOLING.value,
    # A departure reopens one anonymous gap regardless of whether the prior
    # campus action had executed.  The service invalidates/revokes the old
    # action and calendar before this state becomes joinable again.
    (GatheringStatus.EXECUTED.value, GatheringEvent.MEMBER_LEFT): GatheringStatus.POOLING.value,
    (GatheringStatus.ACTIVE.value, GatheringEvent.MEMBER_LEFT): GatheringStatus.POOLING.value,
    (
        GatheringStatus.TENTATIVE.value,
        GatheringEvent.ALL_CONFIRMED,
    ): GatheringStatus.CONFIRMED.value,
    (
        GatheringStatus.CONFIRMED.value,
        GatheringEvent.PREVIEW_CREATED,
    ): GatheringStatus.PREVIEWED.value,
    (
        GatheringStatus.PREVIEWED.value,
        GatheringEvent.ACTION_SUCCEEDED,
    ): GatheringStatus.EXECUTED.value,
    (
        GatheringStatus.PREVIEWED.value,
        GatheringEvent.ACTION_FAILED,
    ): GatheringStatus.CONFIRMED.value,
    (
        GatheringStatus.PREVIEWED.value,
        GatheringEvent.PREVIEW_INVALIDATED,
    ): GatheringStatus.CONFIRMED.value,
    # A campus write is optional. Ordinary confirmed gatherings and a
    # preview that was never authorized still become an activity at the
    # server-owned start boundary; only the external write is skipped.
    (GatheringStatus.CONFIRMED.value, GatheringEvent.START): GatheringStatus.ACTIVE.value,
    (GatheringStatus.PREVIEWED.value, GatheringEvent.START): GatheringStatus.ACTIVE.value,
    (GatheringStatus.EXECUTED.value, GatheringEvent.START): GatheringStatus.ACTIVE.value,
    (GatheringStatus.EXECUTED.value, GatheringEvent.COMPLETE): GatheringStatus.COMPLETED.value,
    (GatheringStatus.ACTIVE.value, GatheringEvent.COMPLETE): GatheringStatus.COMPLETED.value,
    (
        GatheringStatus.COMPLETED.value,
        GatheringEvent.RECUR,
    ): GatheringStatus.RECURRENCE_PENDING.value,
    (GatheringStatus.COMPLETED.value, GatheringEvent.ARCHIVE): GatheringStatus.ARCHIVED.value,
    (
        GatheringStatus.RECURRENCE_PENDING.value,
        GatheringEvent.ARCHIVE,
    ): GatheringStatus.ARCHIVED.value,
    (GatheringStatus.POOLING.value, GatheringEvent.DISSOLVE): GatheringStatus.DISSOLVED.value,
    (GatheringStatus.TENTATIVE.value, GatheringEvent.DISSOLVE): GatheringStatus.DISSOLVED.value,
    (GatheringStatus.TENTATIVE.value, GatheringEvent.RESCHEDULE): GatheringStatus.TENTATIVE.value,
    (GatheringStatus.CONFIRMED.value, GatheringEvent.RESCHEDULE): GatheringStatus.TENTATIVE.value,
    (GatheringStatus.PREVIEWED.value, GatheringEvent.RESCHEDULE): GatheringStatus.TENTATIVE.value,
    (GatheringStatus.EXECUTED.value, GatheringEvent.ROLLBACK): GatheringStatus.CONFIRMED.value,
}


def transition(
    db: Session,
    gathering: Gathering,
    event: GatheringEvent,
    *,
    actor_user_id: str | None = None,
) -> Gathering:
    from_status = gathering.status
    target = TRANSITIONS.get((from_status, event))
    if target is None:
        raise ConflictError(
            "INVALID_GATHERING_TRANSITION",
            f"状态 {from_status} 不接受事件 {event.value}",
            {"status": from_status, "event": event.value},
        )
    gathering.status = target
    if event == GatheringEvent.MATCHED:
        gathering.confirmation_deadline = utcnow() + timedelta(minutes=15)
    elif target != GatheringStatus.TENTATIVE.value:
        gathering.confirmation_deadline = None
    db.add(
        GatheringTransition(
            gathering_id=gathering.id,
            from_status=from_status,
            to_status=target,
            event=event.value,
            actor_user_id=actor_user_id,
        )
    )
    db.flush()
    return gathering
