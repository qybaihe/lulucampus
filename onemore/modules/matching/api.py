from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from onemore.core.auth import require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.modules.matching import service
from onemore.modules.matching.schemas import MatchingRunResult

router = APIRouter(tags=["matching"])


@router.post(
    "/internal/matching/run",
    response_model=APIResponse[MatchingRunResult],
    dependencies=[Depends(require_admin)],
)
def run_matching(db: Session = Depends(get_db)) -> APIResponse[MatchingRunResult]:
    return APIResponse(data=MatchingRunResult.model_validate(service.run_matching(db)))
