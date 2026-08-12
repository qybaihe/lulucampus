from __future__ import annotations

import math
from contextlib import ExitStack
from datetime import UTC, datetime
from itertools import combinations

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from onemore.core.locks import gathering_locks, user_locks
from onemore.core.time import ensure_utc
from onemore.db.models import (
    CompetitionSkill,
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    IntentCard,
    IntentStatus,
    Profile,
    Relation,
    RelationStatus,
    TrustLevel,
    TrustProfile,
    User,
    UserBlock,
)
from onemore.modules.gathering import service as gathering_service
from onemore.modules.gathering.state_machine import GatheringEvent, transition
from onemore.modules.trust.service import LEVEL_ORDER

SIMILAR_WEIGHTS = {
    "time": 0.26,
    "goal": 0.22,
    "campus": 0.12,
    "level": 0.12,
    "taste": 0.14,
    "interaction": 0.09,
    "trust": 0.05,
}

# 广州校区内部（南 / 东 / 北）班车可及，视为同一匹配半径；珠海、深圳单独成池。
_GUANGZHOU_CAMPUSES = frozenset({"南校园", "东校园", "北校园", "广州校区"})


def _campus_compatible(left: str | None, right: str | None) -> bool:
    if not left or not right or left == right:
        return True
    return left in _GUANGZHOU_CAMPUSES and right in _GUANGZHOU_CAMPUSES


def _tokens(value: str) -> set[str]:
    compact = "".join(value.lower().split())
    if len(compact) <= 2:
        return {compact} if compact else set()
    return {compact[index : index + 2] for index in range(len(compact) - 1)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _window_overlap(left: IntentCard, right: IntentCard) -> float:
    best = 0.0
    for l_window in left.available_windows:
        for r_window in right.available_windows:
            try:
                l_start = ensure_utc(datetime.fromisoformat(l_window["start_at"]))
                l_end = ensure_utc(datetime.fromisoformat(l_window["end_at"]))
                r_start = ensure_utc(datetime.fromisoformat(r_window["start_at"]))
                r_end = ensure_utc(datetime.fromisoformat(r_window["end_at"]))
            except (KeyError, TypeError, ValueError):
                continue
            overlap = max(0.0, (min(l_end, r_end) - max(l_start, r_start)).total_seconds())
            base = max(
                1.0, min((l_end - l_start).total_seconds(), (r_end - r_start).total_seconds())
            )
            best = max(best, overlap / base)
    return round(best, 4)


def _relation_bonus(db: Session, user_a: str, user_b: str) -> float:
    first, second = sorted((user_a, user_b))
    exists = db.scalar(
        select(Relation.id).where(
            Relation.participant_a_id == first,
            Relation.participant_b_id == second,
            Relation.status == RelationStatus.ACTIVE.value,
        )
    )
    return 0.15 if exists else 0.0


def _blocked(db: Session, user_a: str, user_b: str) -> bool:
    return (
        db.scalar(
            select(UserBlock.id).where(
                or_(
                    and_(UserBlock.blocker_id == user_a, UserBlock.blocked_id == user_b),
                    and_(UserBlock.blocker_id == user_b, UserBlock.blocked_id == user_a),
                )
            )
        )
        is not None
    )


def _pairwise_block_compatible(db: Session, user_ids: set[str] | list[str]) -> bool:
    return all(not _blocked(db, left, right) for left, right in combinations(user_ids, 2))


def _social_group_compatible(
    db: Session, gathering: Gathering, user_ids: set[str] | list[str]
) -> bool:
    users = [db.get(User, user_id) for user_id in user_ids]
    return all(
        user is not None
        and user.account_status == "active"
        and user.social_enabled
        and gathering.min_size >= user.minimum_group_size
        for user in users
    )


def _cross_college_compatible(db: Session, user_ids: set[str] | list[str]) -> bool:
    users = [db.get(User, user_id) for user_id in user_ids]
    colleges = {
        user.college.strip()
        for user in users
        if user is not None and user.college and user.college.strip()
    }
    if len(colleges) <= 1:
        return True
    return all(
        (trust := db.get(TrustProfile, user_id)) is not None
        and LEVEL_ORDER[trust.level] >= LEVEL_ORDER[TrustLevel.T2.value]
        for user_id in user_ids
    )


def _visible_capability_vector(db: Session, user_id: str) -> dict[str, float]:
    profile = db.get(Profile, user_id)
    if profile is None:
        return {}
    user = db.get(User, user_id)
    if user is None or user.course_matching_enabled:
        return dict(profile.capability_vector)
    # Self-reported + taste-synced tags (taste:*) stay available even when
    # course matching is off — interest signals are intentional opt-in data.
    allowed = set(profile.self_reported_tags)
    return {
        key: value
        for key, value in profile.capability_vector.items()
        if key in allowed or str(key).startswith("taste:")
    }


def _taste_similarity(db: Session, user_a: str, user_b: str) -> float:
    """Overlap of Douyin taste features (persona tags + interest domains)."""
    from onemore.modules.taste_profile.service import taste_feature_set

    left = taste_feature_set(db, user_a)
    right = taste_feature_set(db, user_b)
    if not left and not right:
        return 0.35  # neutral when neither has taste yet
    if not left or not right:
        return 0.2
    return _jaccard(left, right)


def _shared_interest_labels(db: Session, user_ids: list[str]) -> list[str]:
    from onemore.modules.taste_profile.service import public_interest_tags

    counts: dict[str, int] = {}
    for user_id in user_ids:
        for tag in public_interest_tags(db, user_id):
            counts[tag] = counts.get(tag, 0) + 1
    return [
        tag
        for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ]


def _taste_aware_match_reason(
    db: Session, user_ids: list[str], *, complementary: bool
) -> str:
    shared = _shared_interest_labels(db, user_ids)
    if complementary:
        base = "你们的目标一致，时间可行；成员能力覆盖了不同角色。"
        if shared:
            return f"{base}兴趣上也对上了：{'、'.join(shared[:2])}。"
        return base
    if shared:
        return f"兴趣画像相近（{'、'.join(shared[:2])}），时间与目标也对得上。"
    return "你们在时间、目标与参与强度上相近。"


def _take_pairwise_compatible(
    db: Session,
    base_user_ids: set[str] | list[str],
    candidates: list[IntentCard],
    slots: int,
) -> list[IntentCard]:
    selected: list[IntentCard] = []
    base = set(base_user_ids)
    for candidate in candidates:
        peers = {*base, *(item.user_id for item in selected)}
        if all(not _blocked(db, candidate.user_id, peer_id) for peer_id in peers):
            selected.append(candidate)
            if len(selected) >= slots:
                break
    return selected


def _matching_preference_similarity(
    db: Session, source: IntentCard, candidate: IntentCard
) -> float:
    source_user = db.get(User, source.user_id)
    candidate_user = db.get(User, candidate.user_id)
    if source_user is None or candidate_user is None:
        return 0.5
    defaults = {
        "interaction_style": "balanced",
        "sport_level": "casual",
        "study_intensity": "balanced",
    }
    source_preferences = {**defaults, **(source_user.matching_preferences or {})}
    candidate_preferences = {**defaults, **(candidate_user.matching_preferences or {})}
    keys = ["interaction_style"]
    kind = f"{source.gathering_type} {candidate.gathering_type}"
    if any(value in kind for value in ("羽毛球", "篮球", "足球", "运动", "健身")):
        keys.append("sport_level")
    else:
        keys.append("study_intensity")
    exact = sum(
        source_preferences[key] == candidate_preferences[key] for key in keys
    )
    preference_score = exact / len(keys)
    explicit_intensity = 1.0 if source.intensity == candidate.intensity else 0.5
    return (preference_score + explicit_intensity) / 2


def match_similar(db: Session, source: IntentCard, candidate: IntentCard) -> dict:
    source_trust = db.get(TrustProfile, source.user_id)
    candidate_trust = db.get(TrustProfile, candidate.user_id)
    source_tags = set(_visible_capability_vector(db, source.user_id))
    candidate_tags = set(_visible_capability_vector(db, candidate.user_id))
    taste = _taste_similarity(db, source.user_id, candidate.user_id)
    dimensions = {
        "time": _window_overlap(source, candidate),
        "goal": _jaccard(_tokens(source.goal), _tokens(candidate.goal)),
        "campus": 1.0 if _campus_compatible(source.campus, candidate.campus) else 0.0,
        "level": _jaccard(source_tags, candidate_tags),
        "taste": taste,
        "interaction": _matching_preference_similarity(db, source, candidate),
        "trust": (
            1.0
            if source_trust and candidate_trust and source_trust.level == candidate_trust.level
            else 0.5
        ),
    }
    score = sum(SIMILAR_WEIGHTS[key] * value for key, value in dimensions.items())
    score += _relation_bonus(db, source.user_id, candidate.user_id)
    reason = "共同时间稳定，目标与参与强度相近"
    if taste >= 0.45:
        reason = "兴趣画像相近，共同时间与目标也匹配"
        shared = _shared_interest_labels(db, [source.user_id, candidate.user_id])
        if shared:
            reason = f"兴趣画像相近（{'、'.join(shared[:2])}），共同时间与目标也匹配"
    return {
        "score": round(min(score, 1.0), 4),
        "dimensions": dimensions,
        "reason": reason,
    }


def _required_skills(db: Session, card: IntentCard) -> set[str]:
    if card.competition_id:
        skills = set(
            db.scalars(
                select(CompetitionSkill.capability_key).where(
                    CompetitionSkill.competition_id == card.competition_id
                )
            )
        )
        if skills:
            return skills
    return set(card.required_roles)


def match_complementary(
    db: Session,
    source: IntentCard,
    candidates: list[IntentCard],
    slots: int,
    base_user_ids: set[str] | list[str] | None = None,
) -> list[IntentCard]:
    required = _required_skills(db, source)
    selected: list[IntentCard] = []
    covered = set(_visible_capability_vector(db, source.user_id))
    remaining = candidates[:]
    while remaining and len(selected) < slots:
        best: IntentCard | None = None
        best_score = -math.inf
        for candidate in remaining:
            peers = {
                *(base_user_ids or [source.user_id]),
                *(item.user_id for item in selected),
            }
            if any(_blocked(db, candidate.user_id, peer_id) for peer_id in peers):
                continue
            profile = db.get(Profile, candidate.user_id)
            skills = set(_visible_capability_vector(db, candidate.user_id))
            marginal = len((skills - covered) & required) if required else len(skills - covered)
            time_score = _window_overlap(source, candidate)
            campus_score = 1.0 if _campus_compatible(source.campus, candidate.campus) else 0.0
            cross_score = profile.cross_major_score if profile else 0.0
            taste_score = _taste_similarity(db, source.user_id, candidate.user_id)
            score = (
                marginal * 2.0
                + time_score
                + campus_score
                + cross_score
                + taste_score * 0.8
            )
            if score > best_score:
                best, best_score = candidate, score
        if best is None:
            break
        selected.append(best)
        covered.update(_visible_capability_vector(db, best.user_id))
        remaining.remove(best)
    return selected


def _covers_required(db: Session, source: IntentCard, selected: list[IntentCard]) -> bool:
    required = _required_skills(db, source)
    if not required:
        return True
    covered: set[str] = set()
    for card in [source, *selected]:
        covered.update(_visible_capability_vector(db, card.user_id))
        user = db.get(User, card.user_id)
        for item in card.capabilities:
            if item.get("source") == "verified" and (
                user is None or not user.course_matching_enabled
            ):
                continue
            key = item.get("key")
            if isinstance(key, str):
                covered.add(key)
    return required.issubset(covered)


def _verified_gender_code(user: User | None) -> str | None:
    if user is None:
        return None
    code = (user.gender_code or "").strip().lower()
    return code if code not in {"", "unknown", "unspecified"} else None


def _gender_group_compatible(
    db: Session,
    gathering: Gathering,
    existing_user_ids: list[str] | set[str],
    selected: list[IntentCard],
) -> bool:
    users = [
        user
        for user_id in {*existing_user_ids, *(card.user_id for card in selected)}
        if (user := db.get(User, user_id)) is not None
    ]
    if (
        not gathering.same_gender_only
        and not any(card.same_gender_only for card in selected)
        and not any(user.same_gender_only for user in users)
    ):
        return True
    genders = {_verified_gender_code(user) for user in users}
    return None not in genders and len(genders) == 1


def _has_time_conflict(db: Session, user_id: str, gathering: Gathering) -> bool:
    if not gathering.start_at or not gathering.end_at:
        return False
    return (
        db.scalar(
            select(GatheringMember.id)
            .join(Gathering, Gathering.id == GatheringMember.gathering_id)
            .where(
                GatheringMember.user_id == user_id,
                Gathering.status.in_(
                    [
                        GatheringStatus.TENTATIVE.value,
                        GatheringStatus.CONFIRMED.value,
                        GatheringStatus.PREVIEWED.value,
                        GatheringStatus.EXECUTED.value,
                        GatheringStatus.ACTIVE.value,
                    ]
                ),
                Gathering.start_at < gathering.end_at,
                Gathering.end_at > gathering.start_at,
            )
        )
        is not None
    )


def _eligible(db: Session, source: IntentCard, candidate: IntentCard, gathering: Gathering) -> bool:
    if source.user_id == candidate.user_id or _blocked(db, source.user_id, candidate.user_id):
        return False
    trust = db.get(TrustProfile, candidate.user_id)
    if not trust or LEVEL_ORDER[trust.level] < LEVEL_ORDER[gathering.required_trust_level]:
        return False
    if source.gathering_type != candidate.gathering_type or source.mode != candidate.mode:
        return False
    # A candidate's per-intent size range is a real constraint, not display
    # metadata. Target sizes must agree and the source pool must be capable of
    # satisfying the candidate's minimum.
    if (
        candidate.target_size != gathering.target_size
        or candidate.min_size > gathering.target_size
    ):
        return False
    if not _campus_compatible(source.campus, candidate.campus):
        return False
    source_user = db.get(User, source.user_id)
    candidate_user = db.get(User, candidate.user_id)
    if (
        source_user is None
        or candidate_user is None
        or not source_user.social_enabled
        or not candidate_user.social_enabled
        or gathering.min_size < candidate_user.minimum_group_size
    ):
        return False
    if (gathering.same_gender_only or (candidate_user and candidate_user.same_gender_only)) and (
        source_user is None
        or candidate_user is None
        or not _verified_gender_code(source_user)
        or _verified_gender_code(source_user) != _verified_gender_code(candidate_user)
    ):
        return False
    if candidate.same_gender_only and (
        source_user is None
        or candidate_user is None
        or not _verified_gender_code(source_user)
        or _verified_gender_code(source_user) != _verified_gender_code(candidate_user)
    ):
        return False
    if _window_overlap(source, candidate) <= 0:
        return False
    partial_size = db.scalar(
        select(func.count(GatheringMember.id))
        .join(Gathering, Gathering.id == GatheringMember.gathering_id)
        .where(
            Gathering.source_intent_id == candidate.id,
            Gathering.status == GatheringStatus.POOLING.value,
            GatheringMember.left_at.is_(None),
        )
    )
    if partial_size and partial_size > 1:
        return False
    return not _has_time_conflict(db, candidate.user_id, gathering)


def run_matching(db: Session) -> dict:
    # Sweep first so an activity whose real end boundary has passed cannot
    # linger in Pooling merely because a stale expires_at is later.
    gathering_service.dissolve_expired(db)
    now = datetime.now(UTC)
    gatherings = list(
        db.scalars(
            select(Gathering).where(
                Gathering.status == GatheringStatus.POOLING.value,
                or_(Gathering.expires_at.is_(None), Gathering.expires_at > now),
                or_(Gathering.end_at.is_(None), Gathering.end_at > now),
            )
        )
    )
    formed: list[str] = []
    for gathering in gatherings:
        if gathering.status != GatheringStatus.POOLING.value or not gathering.source_intent_id:
            continue
        original_source = db.get(IntentCard, gathering.source_intent_id)
        if original_source is None:
            continue
        current_member_ids = list(
            db.scalars(
                select(GatheringMember.user_id).where(
                    GatheringMember.gathering_id == gathering.id,
                    GatheringMember.left_at.is_(None),
                )
            )
        )
        if not current_member_ids:
            continue
        if not _pairwise_block_compatible(db, current_member_ids):
            continue
        if not _social_group_compatible(db, gathering, current_member_ids):
            continue
        if not _cross_college_compatible(db, current_member_ids):
            continue
        if any(_has_time_conflict(db, user_id, gathering) for user_id in current_member_ids):
            continue
        source = original_source
        if source.user_id not in current_member_ids:
            replacement = db.scalar(
                select(IntentCard)
                .where(
                    IntentCard.user_id.in_(current_member_ids),
                    IntentCard.gathering_type == gathering.gathering_type,
                    IntentCard.mode == gathering.mode,
                    IntentCard.status.in_([IntentStatus.POOLING.value, IntentStatus.MATCHED.value]),
                )
                .order_by(IntentCard.updated_at.desc())
            )
            if replacement is None:
                continue
            source = replacement
        all_candidates = list(
            db.scalars(
                select(IntentCard).where(
                    IntentCard.status == IntentStatus.POOLING.value,
                    IntentCard.id != source.id,
                    IntentCard.user_id.not_in(current_member_ids),
                    IntentCard.expires_at > datetime.now(source.expires_at.tzinfo),
                )
            )
        )
        candidates = [
            card
            for card in all_candidates
            if _eligible(db, source, card, gathering)
            and all(
                not _blocked(db, card.user_id, member_id)
                for member_id in current_member_ids
            )
        ]
        slots = max(0, gathering.target_size - len(current_member_ids))
        if gathering.mode == "complementary":
            chosen = match_complementary(
                db, source, candidates, slots, base_user_ids=current_member_ids
            )
        else:
            ranked = sorted(
                candidates,
                key=lambda card: match_similar(db, source, card)["score"],
                reverse=True,
            )
            chosen = _take_pairwise_compatible(
                db, current_member_ids, ranked, slots
            )
        if gathering.mode == "complementary" and not _covers_required(db, source, chosen):
            continue
        if not _gender_group_compatible(db, gathering, current_member_ids, chosen):
            continue
        if not _cross_college_compatible(
            db, {*current_member_ids, *(card.user_id for card in chosen)}
        ):
            continue
        strict_identity = gathering.identity_disclosure == "after_full" or any(
            card.social_mode == "after_full" for card in chosen
        )
        formation_threshold = max(
            [
                gathering.target_size if strict_identity else gathering.min_size,
                *(card.min_size for card in chosen),
            ]
        )
        if len(chosen) + len(current_member_ids) < formation_threshold:
            continue
        chosen = chosen[:slots]
        user_ids = sorted({*current_member_ids, *(card.user_id for card in chosen)})
        source_gatherings = list(
            db.scalars(
                select(Gathering).where(
                    Gathering.source_intent_id.in_([card.id for card in chosen]),
                    Gathering.status == GatheringStatus.POOLING.value,
                )
            )
        )
        lock_ids = sorted({gathering.id, *(item.id for item in source_gatherings)})
        with ExitStack() as stack:
            for gathering_id in lock_ids:
                stack.enter_context(gathering_locks.acquire(gathering_id))
            for user_id in user_ids:
                stack.enter_context(user_locks.acquire(user_id))
            db.refresh(gathering)
            db.refresh(source)
            if gathering_service.is_expired(gathering):
                gathering_service._finalize_expired_locked(db, gathering)
                db.commit()
                continue
            for card in chosen:
                db.refresh(card)
            locked_member_ids = set(
                db.scalars(
                    select(GatheringMember.user_id).where(
                        GatheringMember.gathering_id == gathering.id,
                        GatheringMember.left_at.is_(None),
                    )
                )
            )
            if any(_has_time_conflict(db, user_id, gathering) for user_id in locked_member_ids):
                continue
            if not _pairwise_block_compatible(db, locked_member_ids):
                continue
            if not _social_group_compatible(db, gathering, locked_member_ids):
                continue
            refreshed_candidates = [
                card
                for card in chosen
                if card.status == IntentStatus.POOLING.value
                and card.user_id not in locked_member_ids
                and _eligible(db, source, card, gathering)
            ]
            chosen = _take_pairwise_compatible(
                db,
                locked_member_ids,
                refreshed_candidates,
                max(0, gathering.target_size - len(locked_member_ids)),
            )
            if gathering.status != GatheringStatus.POOLING.value or (
                len(locked_member_ids) + len(chosen) < formation_threshold
            ):
                continue
            if gathering.mode == "complementary" and not _covers_required(db, source, chosen):
                continue
            if not _gender_group_compatible(db, gathering, locked_member_ids, chosen):
                continue
            if not _cross_college_compatible(
                db, {*locked_member_ids, *(card.user_id for card in chosen)}
            ):
                continue
            if not _pairwise_block_compatible(
                db, {*locked_member_ids, *(card.user_id for card in chosen)}
            ):
                continue
            if any(card.social_mode == "after_full" for card in chosen):
                gathering.identity_disclosure = "after_full"
            if any(card.same_gender_only for card in chosen):
                gathering.same_gender_only = True
            gathering.min_size = max(
                [gathering.min_size, *(card.min_size for card in chosen)]
            )
            for card in chosen:
                if card.user_id not in locked_member_ids:
                    profile = db.get(Profile, card.user_id)
                    role = None
                    visible_capabilities = _visible_capability_vector(db, card.user_id)
                    if profile and visible_capabilities:
                        role = max(
                            visible_capabilities,
                            key=lambda key: visible_capabilities[key],
                        )
                    prior = db.scalar(
                        select(GatheringMember).where(
                            GatheringMember.gathering_id == gathering.id,
                            GatheringMember.user_id == card.user_id,
                        )
                    )
                    if prior:
                        prior.left_at = None
                        prior.role = role
                        prior.joined_via = "matching"
                        prior.confirmation_status = ConfirmationStatus.PENDING.value
                        prior.confirmed_at = None
                    else:
                        db.add(
                            GatheringMember(
                                gathering_id=gathering.id,
                                user_id=card.user_id,
                                role=role,
                                joined_via="matching",
                            )
                        )
                card.status = IntentStatus.MATCHED.value
            chosen_card_ids = {card.id for card in chosen}
            for source_gathering in source_gatherings:
                db.refresh(source_gathering)
                if (
                    source_gathering.id != gathering.id
                    and source_gathering.source_intent_id in chosen_card_ids
                    and source_gathering.status == GatheringStatus.POOLING.value
                ):
                    transition(db, source_gathering, GatheringEvent.DISSOLVE)
                    db.execute(
                        delete(GatheringMember).where(
                            GatheringMember.gathering_id == source_gathering.id
                        )
                    )
            if original_source.status == IntentStatus.POOLING.value:
                original_source.status = IntentStatus.MATCHED.value
            transition(db, gathering, GatheringEvent.MATCHED)
            from onemore.modules.notify.service import notify_confirmation_required

            notify_confirmation_required(db, gathering)
            gathering.match_reason = _taste_aware_match_reason(
                db,
                user_ids,
                complementary=gathering.mode == "complementary",
            )
            formed.append(gathering.id)
            db.commit()
    return {"examined": len(gatherings), "formed": len(formed), "gathering_ids": formed}
