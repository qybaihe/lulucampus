from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from onemore.core.auth import require_admin
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.modules.cast_driver.service import snapshot, tick

router = APIRouter(prefix="/internal/cast-driver", tags=["cast-driver"])


@router.get("/status", response_model=APIResponse[dict], dependencies=[Depends(require_admin)])
def driver_status(db: Session = Depends(get_db)) -> APIResponse[dict]:
    return APIResponse(data=snapshot(db))


@router.post("/tick", response_model=APIResponse[dict], dependencies=[Depends(require_admin)])
def driver_tick(db: Session = Depends(get_db)) -> APIResponse[dict]:
    # Manual tick is an operator tool; still hard-stopped in production inside tick().
    return APIResponse(data=tick(db, force=True, enabled=True))
