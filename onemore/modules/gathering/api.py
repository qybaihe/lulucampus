from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from onemore.core.auth import current_user, require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.gathering import service
from onemore.modules.gathering.schemas import (
    BackfillClaimRequest,
    BackfillFallbackRequest,
    BackfillOpportunityView,
    CompleteRequest,
    ConfirmGatheringRequest,
    DepartedSafetyContextView,
    GapShareView,
    GatheringActionCapabilityView,
    GatheringBookingOptionView,
    GatheringBookingPlanRequest,
    GatheringView,
    IcebreakerView,
    InitiateGatheringRequest,
    JoinGatheringRequest,
    LeaveGatheringRequest,
    RecurRequest,
    RecurringGatheringRequest,
    ReportRequest,
    ReportResolution,
    RescheduleProposalView,
    RescheduleRequest,
    RescheduleVoteRequest,
    SemesterRecapView,
)
from onemore.modules.gathering.share_page import render_share_page
from onemore.modules.schedule.schemas import IntersectionView

router = APIRouter(tags=["gathering"])


def _view(db: Session, gathering, user_id: str | None) -> GatheringView:
    return GatheringView.model_validate(service.to_view(db, gathering, user_id))


@router.get("/shares/g/{share_token}", response_model=APIResponse[GapShareView])
def resolve_gap_share(
    share_token: str, db: Session = Depends(get_db)
) -> APIResponse[GapShareView]:
    """Resolve an opaque link without exposing members or owner identity."""

    return APIResponse(data=GapShareView.model_validate(service.gap_share_view(db, share_token)))


@router.get("/g/{share_token}", response_class=HTMLResponse, include_in_schema=False)
def gap_share_landing(share_token: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """站外可看的匿名缺口卡落地页（班级群/宿舍群的自然传播物）。"""

    view = service.gap_share_view(db, share_token)
    return HTMLResponse(render_share_page(view))


@router.post(
    "/shares/g/{share_token}/join",
    response_model=APIResponse[GatheringView],
)
def join_gap_share(
    share_token: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    gathering_id = service.resolve_gap_share_token(share_token)
    gathering = service.join(db, gathering_id, user, role=None, joined_via="share")
    return APIResponse(data=_view(db, gathering, user.id))


@router.get("/gatherings/mine", response_model=APIResponse[list[GatheringView]])
def my_gatherings(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> APIResponse[list[GatheringView]]:
    return APIResponse(data=[_view(db, item, user.id) for item in service.list_mine(db, user.id)])


@router.get("/gatherings/open", response_model=APIResponse[list[GatheringView]])
def open_gatherings(
    campus: str | None = Query(default=None),
    gathering_type: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[GatheringView]]:
    return APIResponse(
        data=[
            _view(db, item, user.id)
            for item in service.list_open(
                db,
                viewer_id=user.id,
                campus=campus,
                gathering_type=gathering_type,
            )
        ]
    )


@router.post(
    "/gatherings/initiate",
    response_model=APIResponse[GatheringView],
    status_code=status.HTTP_201_CREATED,
)
def initiate_gathering(
    body: InitiateGatheringRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    item = service.initiate(db, user, body)
    return APIResponse(data=_view(db, item, user.id))


@router.get(
    "/gatherings/history/safety",
    response_model=APIResponse[list[DepartedSafetyContextView]],
)
def departed_gathering_safety_history(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[DepartedSafetyContextView]]:
    return APIResponse(
        data=[
            DepartedSafetyContextView.model_validate(item)
            for item in service.departed_safety_history(db, user.id)
        ]
    )


@router.get("/gatherings/{gathering_id}", response_model=APIResponse[GatheringView])
def gathering_detail(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    return APIResponse(
        data=_view(
            db,
            service.get_gathering_for_viewer(db, gathering_id, user.id),
            user.id,
        )
    )


@router.get(
    "/gatherings/{gathering_id}/action-capability",
    response_model=APIResponse[GatheringActionCapabilityView],
)
def gathering_action_capability(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringActionCapabilityView]:
    return APIResponse(
        data=GatheringActionCapabilityView.model_validate(
            service.gathering_action_capability(db, gathering_id, user.id)
        )
    )


@router.get(
    "/gatherings/{gathering_id}/booking-options",
    response_model=APIResponse[list[GatheringBookingOptionView]],
)
def gathering_booking_options(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[GatheringBookingOptionView]]:
    return APIResponse(
        data=[
            GatheringBookingOptionView.model_validate(item)
            for item in service.booking_options(db, gathering_id, user.id)
        ]
    )


@router.post(
    "/gatherings/{gathering_id}/booking-plan",
    response_model=APIResponse[GatheringView],
)
def select_gathering_booking_plan(
    gathering_id: str,
    body: GatheringBookingPlanRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    item = service.select_booking_plan(db, gathering_id, user.id, body.option_token)
    return APIResponse(data=_view(db, item, user.id))


@router.post(
    "/gatherings/{gathering_id}/share",
    response_model=APIResponse[GapShareView],
    status_code=status.HTTP_201_CREATED,
)
def create_gap_share(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GapShareView]:
    return APIResponse(
        data=GapShareView.model_validate(service.create_gap_share(db, gathering_id, user.id))
    )


@router.post("/gatherings/{gathering_id}/join", response_model=APIResponse[GatheringView])
def join_gathering(
    gathering_id: str,
    body: JoinGatheringRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    # The provenance is server-owned; clients cannot claim to have arrived via
    # a share, matching job, or backfill fast lane.
    gathering = service.join(db, gathering_id, user, body.role, "open")
    return APIResponse(data=_view(db, gathering, user.id))


@router.post("/gatherings/{gathering_id}/confirm", response_model=APIResponse[GatheringView])
def confirm_gathering(
    gathering_id: str,
    body: ConfirmGatheringRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    gathering = service.confirm(db, gathering_id, user.id, body.confirmed)
    return APIResponse(data=_view(db, gathering, user.id))


@router.post("/gatherings/{gathering_id}/leave", response_model=APIResponse[dict])
def leave_gathering(
    gathering_id: str,
    body: LeaveGatheringRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    gathering = service.leave(db, gathering_id, user.id, body.reason)
    return APIResponse(data={"id": gathering.id, "status": gathering.status})


@router.get(
    "/gatherings/{gathering_id}/time-options",
    response_model=APIResponse[list[IntersectionView]],
)
def gathering_time_options(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[IntersectionView]]:
    return APIResponse(data=service.time_options(db, gathering_id, user.id))


@router.get(
    "/gatherings/{gathering_id}/reschedule",
    response_model=APIResponse[RescheduleProposalView | None],
)
def current_reschedule(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[RescheduleProposalView | None]:
    proposal = service.current_reschedule_proposal(db, gathering_id, user.id)
    return APIResponse(
        data=(
            RescheduleProposalView.model_validate(
                service.reschedule_proposal_view(db, proposal, user.id)
            )
            if proposal is not None
            else None
        )
    )


@router.post(
    "/gatherings/{gathering_id}/reschedule",
    response_model=APIResponse[RescheduleProposalView],
)
def reschedule_gathering(
    gathering_id: str,
    body: RescheduleRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[RescheduleProposalView]:
    proposal = service.propose_reschedule(db, gathering_id, user.id, body.start_at, body.end_at)
    return APIResponse(
        data=RescheduleProposalView.model_validate(
            service.reschedule_proposal_view(db, proposal, user.id)
        )
    )


@router.post(
    "/gatherings/{gathering_id}/reschedule/{proposal_id}/vote",
    response_model=APIResponse[RescheduleProposalView],
)
def vote_on_reschedule(
    gathering_id: str,
    proposal_id: str,
    body: RescheduleVoteRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[RescheduleProposalView]:
    proposal = service.vote_reschedule(
        db, gathering_id, proposal_id, user.id, body.accepted
    )
    return APIResponse(
        data=RescheduleProposalView.model_validate(
            service.reschedule_proposal_view(db, proposal, user.id)
        )
    )


@router.get(
    "/gatherings/{gathering_id}/icebreaker",
    response_model=APIResponse[IcebreakerView],
)
def gathering_icebreaker(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[IcebreakerView]:
    """成局后 30 秒破冰包：为什么是你们 / 第一句怎么开 / 下一步是什么。"""

    return APIResponse(
        data=IcebreakerView.model_validate(
            service.icebreaker_view(db, gathering_id, user.id)
        )
    )


@router.get("/me/recap", response_model=APIResponse[SemesterRecapView])
def my_semester_recap(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[SemesterRecapView]:
    """学期成局回忆录：低频高价值的事实聚合，自带匿名分享文案。"""

    return APIResponse(
        data=SemesterRecapView.model_validate(service.semester_recap(db, user.id))
    )


@router.post("/gatherings/{gathering_id}/complete", response_model=APIResponse[GatheringView])
def complete_gathering(
    gathering_id: str,
    body: CompleteRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    gathering = service.complete(db, gathering_id, user.id, body.completed)
    return APIResponse(data=_view(db, gathering, user.id))


@router.post(
    "/gatherings/{gathering_id}/recur",
    response_model=APIResponse[GatheringView],
    status_code=status.HTTP_201_CREATED,
)
def recur_gathering(
    gathering_id: str,
    body: RecurRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    clone = service.recur(db, gathering_id, user.id, body.keep_user_ids)
    return APIResponse(data=_view(db, clone, user.id))


@router.post(
    "/gatherings/{gathering_id}/recur/finish",
    response_model=APIResponse[dict],
)
def finish_recurrence_choice(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    return APIResponse(
        data=service.finish_recurrence_choice(db, gathering_id, user.id)
    )


@router.post(
    "/gatherings/{gathering_id}/recurring",
    response_model=APIResponse[list[GatheringView]],
    status_code=status.HTTP_201_CREATED,
)
def create_recurring_gatherings(
    gathering_id: str,
    body: RecurringGatheringRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[GatheringView]]:
    items = service.create_recurring_series(db, gathering_id, user.id, body)
    return APIResponse(data=[_view(db, item, user.id) for item in items])


@router.get(
    "/gatherings/{gathering_id}/backfill",
    response_model=APIResponse[BackfillOpportunityView],
)
def backfill_opportunity(
    gathering_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[BackfillOpportunityView]:
    return APIResponse(
        data=BackfillOpportunityView.model_validate(
            service.backfill_opportunity(db, gathering_id, user.id)
        )
    )


@router.post(
    "/gatherings/{gathering_id}/backfill/claim",
    response_model=APIResponse[GatheringView],
)
def claim_backfill(
    gathering_id: str,
    body: BackfillClaimRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    item = service.claim_backfill(db, gathering_id, user, body.role)
    return APIResponse(data=_view(db, item, user.id))


@router.post(
    "/gatherings/{gathering_id}/backfill/fallback",
    response_model=APIResponse[GatheringView],
)
def apply_backfill_fallback(
    gathering_id: str,
    body: BackfillFallbackRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[GatheringView]:
    item = service.apply_backfill_fallback(
        db, gathering_id, user.id, body.option_key
    )
    return APIResponse(data=_view(db, item, user.id))


@router.post("/gatherings/{gathering_id}/report", response_model=APIResponse[dict])
def report_member(
    gathering_id: str,
    body: ReportRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    report = service.report_user(
        db,
        gathering_id,
        user.id,
        body.reported_user_id,
        body.reason,
        body.block,
    )
    return APIResponse(data={"report_id": report.id, "status": report.status})


@router.post(
    "/internal/reports/{report_id}/resolve",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_admin)],
)
def resolve_report(
    report_id: str, body: ReportResolution, db: Session = Depends(get_db)
) -> APIResponse[dict]:
    report = service.resolve_report(db, report_id, body.valid)
    return APIResponse(data={"report_id": report.id, "status": report.status})
