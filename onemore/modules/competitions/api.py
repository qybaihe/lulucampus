from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from onemore.core.auth import optional_user, require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.competitions import service
from onemore.modules.competitions.recommendation import RECOMMENDATION_TIER_PATTERN
from onemore.modules.competitions.schemas import (
    CompetitionSnapshot,
    CompetitionTeamView,
    CompetitionView,
    IngestResult,
    RecommendationTierView,
)

router = APIRouter(tags=["competitions"])


@router.get("/competitions", response_model=APIResponse[list[CompetitionView]])
def competitions(
    direction: str | None = Query(default=None),
    mode: str | None = Query(default=None),
    deadline_before: datetime | None = Query(default=None),
    team_only: bool | None = Query(default=None),
    recommendation_tier: str | None = Query(
        default=None,
        pattern=RECOMMENDATION_TIER_PATTERN,
        description="Filter by storage code A|B|C. Prefer labels from GET /competitions/recommendation-tiers.",
    ),
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[list[CompetitionView]]:
    views = service.list_actionable(
        db,
        direction=direction,
        mode=mode,
        deadline_before=deadline_before,
        team_only=team_only,
        recommendation_tier=recommendation_tier,
        viewer_id=user.id if user else None,
    )
    return APIResponse(data=[CompetitionView.model_validate(item) for item in views])


@router.get(
    "/competitions/recommendation-tiers",
    response_model=APIResponse[list[RecommendationTierView]],
)
def competition_recommendation_tiers() -> APIResponse[list[RecommendationTierView]]:
    """User-facing recommendation tier catalog for filter chips (not a difficulty rank)."""
    return APIResponse(
        data=[
            RecommendationTierView.model_validate(item)
            for item in service.list_recommendation_tiers()
        ]
    )


@router.get("/competitions/{competition_id}", response_model=APIResponse[CompetitionView])
def competition_detail(
    competition_id: str,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> APIResponse[CompetitionView]:
    return APIResponse(
        data=CompetitionView.model_validate(
            service.get_actionable(
                db, competition_id, viewer_id=user.id if user else None
            )
        )
    )


@router.get(
    "/competitions/{competition_id}/teams",
    response_model=APIResponse[list[CompetitionTeamView]],
)
def competition_teams(
    competition_id: str, db: Session = Depends(get_db)
) -> APIResponse[list[CompetitionTeamView]]:
    """招募中的赛事队伍（匿名：规模 / 池内人数 / 角色缺口，无成员身份）。"""
    return APIResponse(
        data=[
            CompetitionTeamView.model_validate(item)
            for item in service.list_teams(db, competition_id)
        ]
    )


@router.post(
    "/internal/competitions/ingest",
    response_model=APIResponse[IngestResult],
    dependencies=[Depends(require_admin)],
)
def ingest_competitions(
    snapshot: CompetitionSnapshot, db: Session = Depends(get_db)
) -> APIResponse[IngestResult]:
    return APIResponse(data=IngestResult.model_validate(service.ingest_snapshot(db, snapshot)))
