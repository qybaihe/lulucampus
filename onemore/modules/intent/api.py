from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.database import get_db
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.intent import service
from onemore.modules.intent.schemas import (
    IntentCardPatch,
    IntentCardView,
    IntentClarificationQuestion,
    IntentCompileRequest,
    IntentCompileResult,
    IntentPublishRequest,
    IntentPublishResult,
)

router = APIRouter(tags=["intent"])


def _view(card) -> IntentCardView:
    return IntentCardView.model_validate(service.card_view_dict(card))


@router.post("/intent/compile", response_model=APIResponse[IntentCompileResult])
def compile_intent(
    body: IntentCompileRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[IntentCompileResult]:
    card, questions = service.compile_intent(db, user, body)
    taste = service.taste_compile_meta(db, user, card)
    return APIResponse(
        data=IntentCompileResult(
            card=_view(card),
            needs_clarification=bool(questions),
            questions=[IntentClarificationQuestion.model_validate(item) for item in questions],
            taste_fit_label=taste.get("taste_fit_label"),
            recruit_hints=taste.get("recruit_hints") or [],
        )
    )


@router.get("/intent/{card_id}", response_model=APIResponse[IntentCardView])
def get_intent(
    card_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[IntentCardView]:
    return APIResponse(data=_view(service.get_card(db, card_id, user.id)))


@router.get(
    "/intent/{card_id}/publication",
    response_model=APIResponse[IntentPublishResult],
)
def get_intent_publication(
    card_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[IntentPublishResult]:
    card, gathering = service.publication(db, card_id, user.id)
    return APIResponse(
        data=IntentPublishResult(
            intent_id=card.id,
            gathering_id=gathering.id,
            status=card.status,
            expires_at=card.expires_at,
        )
    )


@router.patch("/intent/{card_id}", response_model=APIResponse[IntentCardView])
def edit_intent(
    card_id: str,
    body: IntentCardPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[IntentCardView]:
    return APIResponse(data=_view(service.edit_card(db, card_id, user.id, body)))


@router.post(
    "/intent/publish",
    response_model=APIResponse[IntentPublishResult],
    status_code=status.HTTP_201_CREATED,
)
def publish_intent(
    body: IntentPublishRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[IntentPublishResult]:
    card, gathering = service.publish(db, body.card_id, user)
    return APIResponse(
        data=IntentPublishResult(
            intent_id=card.id,
            gathering_id=gathering.id,
            status=card.status,
            expires_at=card.expires_at,
        )
    )


@router.delete("/intent/{card_id}", response_model=APIResponse[dict])
def withdraw_intent(
    card_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[dict]:
    card = service.withdraw(db, card_id, user.id)
    return APIResponse(data={"id": card.id, "status": card.status})
