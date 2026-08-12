from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from onemore.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from onemore.core.time import ensure_utc
from onemore.db.models import (
    CompetitionConstraint,
    CompetitionEvent,
    CompetitionSkill,
    CompetitionStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    IntentCard,
    IntentStatus,
    Profile,
    TimeWindow,
    User,
)
from onemore.modules.gathering.state_machine import GatheringEvent, transition
from onemore.modules.intent.schemas import IntentCardPatch, IntentCompileRequest
from onemore.modules.trust import service as trust_service

TYPE_RULES = [
    (("比赛", "大赛", "黑客松", "竞赛"), ("比赛组队", "complementary")),
    (("项目", "课题", "组队"), ("项目组队", "complementary")),
    (("羽毛球", "篮球", "足球", "网球", "跑步", "健身"), ("运动搭子", "similar")),
    (("ddl", "作业", "冲刺"), ("DDL冲刺", "similar")),
    (("自习", "复习", "学习"), ("自习搭子", "similar")),
    (("活动", "讲座", "宣讲会"), ("活动同行", "similar")),
]
ROLE_KEYWORDS = {
    "前端": "frontend",
    "后端": "backend",
    "产品": "product",
    "视觉": "visual_design",
    "设计": "design",
    "算法": "machine_learning",
    "运营": "operations",
}


def _roles_from_answer(value: str) -> list[str]:
    roles: set[str] = set()
    for raw in re.split(r"[,，、/；;\s]+", value.strip()):
        if not raw:
            continue
        mapped = ROLE_KEYWORDS.get(raw, raw.lower())
        normalized = re.sub(r"[^a-z0-9_\-\u4e00-\u9fff]", "", mapped)[:64]
        if normalized:
            roles.add(normalized)
    return sorted(roles)


def _window_from_answer(value: str) -> dict[str, Any] | None:
    """Parse the exact RFC3339 pair emitted by the native date pickers."""

    try:
        start_raw, end_raw = value.split("|", 1)
        start = ensure_utc(datetime.fromisoformat(start_raw.replace("Z", "+00:00")))
        end = ensure_utc(datetime.fromisoformat(end_raw.replace("Z", "+00:00")))
    except (ValueError, TypeError):
        return None
    if end <= start or start <= datetime.now(UTC):
        return None
    return {"start_at": start.isoformat(), "end_at": end.isoformat(), "stability": 1.0}


def _classify(text: str) -> tuple[str, str]:
    lowered = text.lower()
    for keywords, result in TYPE_RULES:
        if any(keyword.lower() in lowered for keyword in keywords):
            return result
    return "通用搭子", "similar"


def _parse_target_size(text: str, default: int) -> int:
    match = re.search(r"([2-9]|1\d|20)\s*人", text)
    return int(match.group(1)) if match else default


def _card_view_dict(card: IntentCard) -> dict:
    return {
        "id": card.id,
        "status": card.status,
        "gathering_type": card.gathering_type,
        "mode": card.mode,
        "goal": card.goal,
        "mood_note": card.mood_note,
        "capabilities": card.capabilities,
        "required_roles": card.required_roles,
        "intensity": card.intensity,
        "available_windows": card.available_windows,
        "campus": card.campus,
        "min_size": card.min_size,
        "target_size": card.target_size,
        "social_mode": card.social_mode,
        "same_gender_only": card.same_gender_only,
        "competition_id": card.competition_id,
        "expires_at": card.expires_at,
        "field_sources": card.field_sources,
        "clarification_rounds": card.clarification_rounds,
    }


def compile_intent(
    db: Session, user: User, body: IntentCompileRequest
) -> tuple[IntentCard, list[dict[str, str]]]:
    gathering_type, mode = _classify(body.text)
    profile = db.get(Profile, user.id)
    capabilities: list[dict] = []
    if profile:
        visible_verified = (
            set(profile.verified_tags) - set(profile.hidden_verified_tags)
            if user.course_matching_enabled
            else set()
        )
        capabilities.extend(
            {"key": tag, "source": "verified"}
            for tag in sorted(visible_verified)
        )
        capabilities.extend(
            {"key": tag, "source": "self_reported"}
            for tag in profile.self_reported_tags
            if tag not in visible_verified
        )
    required_roles = [value for key, value in ROLE_KEYWORDS.items() if key in body.text]
    if body.answers.get("required_roles"):
        required_roles = _roles_from_answer(body.answers["required_roles"])
    default_size = max(user.minimum_group_size, 4 if mode == "complementary" else 3)
    target_size = max(user.minimum_group_size, _parse_target_size(body.text, default_size))
    min_size = (
        target_size
        if mode == "complementary"
        else min(target_size, user.minimum_group_size)
    )
    if body.competition_id:
        competition = db.scalar(
            select(CompetitionEvent).where(
                CompetitionEvent.id == body.competition_id,
                CompetitionEvent.status == CompetitionStatus.ACTIONABLE.value,
                CompetitionEvent.verification_status == "actionable",
            )
        )
        if competition is None:
            raise NotFoundError("可报名赛事", body.competition_id)
        constraint = db.get(CompetitionConstraint, competition.id)
        skills = list(
            db.scalars(
                select(CompetitionSkill.capability_key).where(
                    CompetitionSkill.competition_id == competition.id
                )
            )
        )
        required_roles = sorted(set(required_roles) | set(skills))
        if constraint and constraint.team_size_max == 1:
            gathering_type, mode = "比赛备赛搭子", "similar"
            target_size = max(
                2,
                _parse_target_size(body.text, max(user.minimum_group_size, 3)),
            )
            min_size = min(target_size, user.minimum_group_size)
        else:
            gathering_type, mode = "比赛组队", "complementary"
        if constraint and constraint.team_size_max > 1:
            if user.minimum_group_size > constraint.team_size_max:
                raise ConflictError(
                    "GROUP_SIZE_PREFERENCE_CONFLICT",
                    "你的最低成局人数高于该赛事允许的队伍上限，请先调整隐私设置",
                    {
                        "minimum_group_size": user.minimum_group_size,
                        "competition_team_size_max": constraint.team_size_max,
                    },
                )
            requested_size = _parse_target_size(body.text, constraint.team_size_max)
            target_size = min(
                constraint.team_size_max,
                max(
                    user.minimum_group_size,
                    constraint.team_size_min,
                    requested_size,
                ),
            )
            min_size = max(user.minimum_group_size, constraint.team_size_min)
    windows = list(
        db.scalars(
            select(TimeWindow)
            .where(TimeWindow.user_id == user.id, TimeWindow.start_at > datetime.now(UTC))
            .order_by(TimeWindow.stability.desc(), TimeWindow.start_at)
            .limit(8)
        )
    )
    available = [
        {
            "start_at": item.start_at.isoformat(),
            "end_at": item.end_at.isoformat(),
            "stability": item.stability,
        }
        for item in windows
    ]

    supplied_window = _window_from_answer(body.answers.get("availability", ""))
    if supplied_window is not None:
        available = [supplied_window]

    questions: list[dict[str, str]] = []
    if not available:
        questions.append(
            {
                "key": "availability",
                "prompt": "选择一个你方便的具体时段",
                "input_type": "time_window",
            }
        )
    if mode == "complementary" and not required_roles and not body.competition_id:
        questions.append(
            {
                "key": "required_roles",
                "prompt": "这次最缺哪些角色或能力？",
                "input_type": "role_list",
            }
        )
    if body.clarification_round >= 2:
        questions = []
    status = IntentStatus.NEEDS_CLARIFICATION.value if questions else IntentStatus.DRAFT.value
    mood_note = (body.mood_note or "").strip() or None
    card = IntentCard(
        user_id=user.id,
        status=status,
        gathering_type=gathering_type,
        mode=mode,
        goal=body.answers.get("goal", body.text.strip()),
        mood_note=mood_note,
        capabilities=capabilities,
        required_roles=required_roles,
        intensity=body.answers.get(
            "intensity",
            (user.matching_preferences or {}).get("study_intensity", "balanced"),
        ),
        available_windows=available,
        campus=user.campus,
        min_size=min_size,
        target_size=target_size,
        social_mode="after_full",
        same_gender_only=user.same_gender_only,
        competition_id=body.competition_id,
        expires_at=datetime.now(UTC) + timedelta(days=3),
        clarification_rounds=body.clarification_round,
        clarification_questions=questions,
        field_sources={
            "gathering_type": "ai_inferred",
            "goal": "user_input",
            **({"mood_note": "user_input"} if mood_note else {}),
            "capabilities": "profile_prefill",
            "required_roles": (
                "user_input" if body.answers.get("required_roles") else "ai_inferred"
            ),
            "intensity": (
                "user_input" if body.answers.get("intensity") else "matching_preference"
            ),
            "available_windows": (
                "user_input" if supplied_window is not None else "schedule_prefill"
            ),
            "campus": "school_record",
            "social_mode": "default",
            "same_gender_only": "privacy_default",
            "expires_at": "default",
        },
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card, questions


def get_card(db: Session, card_id: str, user_id: str) -> IntentCard:
    card = db.get(IntentCard, card_id)
    if card is None:
        raise NotFoundError("意图卡", card_id)
    if card.user_id != user_id:
        raise ForbiddenError()
    return card


def publication(db: Session, card_id: str, user_id: str) -> tuple[IntentCard, Gathering]:
    card = get_card(db, card_id, user_id)
    gathering = db.scalar(select(Gathering).where(Gathering.source_intent_id == card.id))
    if gathering is None:
        raise NotFoundError("意图发布结果", card_id)
    return card, gathering


def edit_card(db: Session, card_id: str, user_id: str, patch: IntentCardPatch) -> IntentCard:
    card = get_card(db, card_id, user_id)
    if card.status not in {IntentStatus.DRAFT.value, IntentStatus.NEEDS_CLARIFICATION.value}:
        raise ConflictError("INTENT_NOT_EDITABLE", "当前意图卡已不可编辑")
    # Keep SQL DateTime values as Python datetimes.  ``mode="json"`` turns
    # ``expires_at`` into an RFC3339 string, which SQLite's DateTime binder
    # correctly rejects.  The windows column is JSON, so only that nested
    # value is converted back to JSON-compatible RFC3339 strings.
    changes = patch.model_dump(exclude_none=True)
    if patch.available_windows is not None:
        changes["available_windows"] = [
            window.model_dump(mode="json") for window in patch.available_windows
        ]
    if patch.expires_at is not None:
        changes["expires_at"] = ensure_utc(patch.expires_at)
    final_min_size = int(changes.get("min_size", card.min_size))
    final_target_size = int(changes.get("target_size", card.target_size))
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", user_id)
    if final_min_size < user.minimum_group_size:
        raise AppError(
            "GROUP_SIZE_BELOW_PREFERENCE",
            "最低人数不能低于你的个人设置",
            422,
            {"minimum_group_size": user.minimum_group_size},
        )
    if final_min_size > final_target_size:
        raise AppError("INVALID_GROUP_SIZE", "最低人数不能超过目标人数", 422)
    if changes.get("same_gender_only") is True and (
        user.gender_code or ""
    ).strip().lower() in {"", "unknown", "unspecified"}:
        raise AppError(
            "VERIFIED_GENDER_REQUIRED",
            "本次同性局需要已核验的身份信息",
            422,
        )
    if "capabilities" in changes:
        profile = db.get(Profile, user_id)
        verified = set(profile.verified_tags if profile else [])
        normalized: list[dict] = []
        for item in changes["capabilities"]:
            if item["source"] == "verified" and item["key"] not in verified:
                raise AppError("FORGED_VERIFIED_TAG", "已验证标签不可伪造", 422)
            normalized.append(item)
        changes["capabilities"] = normalized
    for field, value in changes.items():
        setattr(card, field, value)
    card.edited_fields = sorted(set(card.edited_fields) | set(changes))
    card.status = IntentStatus.DRAFT.value
    db.commit()
    db.refresh(card)
    return card


def publish(db: Session, card_id: str, user: User) -> tuple[IntentCard, Gathering]:
    if not user.social_enabled:
        raise AppError("SOCIAL_DISABLED", "请先主动开启社交开关", 403)
    trust_service.require_unlock(db, user.id, "create_intent")
    card = get_card(db, card_id, user.id)
    if ensure_utc(card.expires_at) <= datetime.now(UTC):
        card.status = IntentStatus.EXPIRED.value
        db.commit()
        raise AppError("INTENT_EXPIRED", "意图卡已过期，请重新描述需求", 410)
    if card.status != IntentStatus.DRAFT.value:
        raise ConflictError("INTENT_NOT_READY", "意图卡仍需补充或已经发布")
    if card.min_size < user.minimum_group_size or card.target_size < user.minimum_group_size:
        raise ConflictError(
            "GROUP_SIZE_PREFERENCE_CHANGED",
            "个人最低成局人数已变化，请重新确认意图卡",
            {"minimum_group_size": user.minimum_group_size},
        )
    if card.mode == "complementary":
        trust_service.require_unlock(db, user.id, "competition_pool")
    if card.min_size <= 2:
        trust_service.require_unlock(db, user.id, "duo_gathering")
    if card.target_size >= 6:
        trust_service.require_unlock(db, user.id, "large_group")
    first_window = card.available_windows[0] if card.available_windows else None
    gathering = Gathering(
        source_intent_id=card.id,
        owner_user_id=user.id,
        gathering_type=card.gathering_type,
        mode=card.mode,
        title=card.goal[:120],
        goal=card.goal,
        status=GatheringStatus.POOLING.value,
        min_size=card.min_size,
        target_size=card.target_size,
        required_trust_level=(
            "T3"
            if card.target_size >= 6
            else "T2"
            if card.mode == "complementary" or card.min_size <= 2
            else "T1"
        ),
        campus=card.campus,
        same_gender_only=card.same_gender_only or user.same_gender_only,
        identity_disclosure=card.social_mode,
        start_at=(datetime.fromisoformat(first_window["start_at"]) if first_window else None),
        end_at=(datetime.fromisoformat(first_window["end_at"]) if first_window else None),
        required_roles=card.required_roles,
        expires_at=card.expires_at,
    )
    db.add(gathering)
    db.flush()
    db.add(
        GatheringMember(
            gathering_id=gathering.id,
            user_id=user.id,
            role=(card.capabilities[0]["key"] if card.capabilities else None),
            joined_via="owner",
        )
    )
    card.status = IntentStatus.POOLING.value
    db.commit()
    db.refresh(gathering)
    return card, gathering


def withdraw(db: Session, card_id: str, user_id: str) -> IntentCard:
    card = get_card(db, card_id, user_id)
    if card.status not in {
        IntentStatus.DRAFT.value,
        IntentStatus.NEEDS_CLARIFICATION.value,
        IntentStatus.POOLING.value,
    }:
        raise ConflictError("INTENT_NOT_WITHDRAWABLE", "当前意图状态不可撤回")
    card.status = IntentStatus.WITHDRAWN.value
    gatherings = list(
        db.scalars(
            select(Gathering)
            .where(
                Gathering.status == GatheringStatus.POOLING.value,
                Gathering.source_intent_id == card.id,
            )
        )
    )
    for gathering in gatherings:
        transition(db, gathering, GatheringEvent.DISSOLVE, actor_user_id=user_id)
        db.execute(delete(GatheringMember).where(GatheringMember.gathering_id == gathering.id))
    db.commit()
    return card


def expire_sweep(db: Session) -> int:
    expired = list(
        db.scalars(
            select(IntentCard).where(
                IntentCard.status == IntentStatus.POOLING.value,
                IntentCard.expires_at <= datetime.now(UTC),
            )
        )
    )
    for card in expired:
        withdraw(db, card.id, card.user_id)
        card.status = IntentStatus.EXPIRED.value
    db.commit()
    return len(expired)


def taste_compile_meta(db: Session, user: User, card: IntentCard) -> dict[str, Any]:
    """Attach persona-aware recruit hints when compiling an intent."""
    from onemore.modules.taste_profile.competition_match import score_competition
    from onemore.modules.taste_profile.service import persona_dict

    persona = persona_dict(db, user.id)
    if persona is None:
        return {}
    competition_view: dict[str, Any] = {
        "name": card.goal,
        "tracks": [card.gathering_type],
        "required_skills": [{"key": key} for key in (card.required_roles or [])],
        "priority": 0,
        "recommendation_tier": "B",
    }
    if card.competition_id:
        from onemore.modules.competitions.service import get_actionable
        from onemore.core.errors import NotFoundError

        try:
            competition_view = get_actionable(db, card.competition_id)
        except NotFoundError:
            pass
    scored = score_competition(persona, competition_view)
    return {
        "taste_fit_label": scored.get("taste_fit_label"),
        "recruit_hints": scored.get("recruit_hints") or [],
    }


card_view_dict = _card_view_dict
