from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.errors import AppError, NotFoundError
from onemore.core.time import ensure_utc
from onemore.db.models import (
    CapabilityTag,
    CompetitionConstraint,
    CompetitionEvent,
    CompetitionSkill,
    CompetitionStatus,
)
from onemore.modules.competitions.recommendation import (
    recommendation_fields,
    recommendation_tier_catalog,
)
from onemore.modules.competitions.schemas import CompetitionSnapshot, SnapshotCompetition

ACTIONABLE_STATUSES = {"actionable", "verified_actionable", "可行动"}
TRACK_RULES = {
    "前端": "frontend",
    "web": "frontend",
    "后端": "backend",
    "服务端": "backend",
    "人工智能": "machine_learning",
    "ai": "machine_learning",
    "算法": "machine_learning",
    "视觉": "visual_design",
    "设计": "design",
    "产品": "product",
    "商业": "business_analysis",
    "数据": "data_analysis",
}


def verify_gate(item: SnapshotCompetition) -> bool:
    return item.verification_status.strip().lower() in ACTIONABLE_STATUSES


def map_tracks_to_skills(item: SnapshotCompetition, known: set[str]) -> list[str]:
    mapped = set(item.required_skills)
    for track in item.tracks:
        lowered = track.lower()
        for keyword, capability in TRACK_RULES.items():
            if keyword.lower() in lowered:
                mapped.add(capability)
                break
    unknown = sorted(mapped - known)
    if unknown:
        raise AppError(
            "UNKNOWN_CAPABILITY_MAPPING",
            "赛事能力标签未落在课程能力标签空间",
            422,
            {"external_key": item.external_key, "unknown": unknown},
        )
    return sorted(mapped)


def ingest_snapshot(db: Session, snapshot: CompetitionSnapshot) -> dict:
    known = set(db.scalars(select(CapabilityTag.key)))
    deduped: dict[str, SnapshotCompetition] = {}
    duplicate_count = 0
    rejected = 0
    for item in snapshot.items:
        if not verify_gate(item):
            rejected += 1
            continue
        if item.external_key in deduped:
            duplicate_count += 1
            if item.priority < deduped[item.external_key].priority:
                continue
        deduped[item.external_key] = item

    prepared: list[tuple[SnapshotCompetition, list[str]]] = []
    for item in deduped.values():
        prepared.append((item, map_tracks_to_skills(item, known)))

    accepted_ids: list[str] = []
    try:
        for item, skills in prepared:
            event = db.scalar(
                select(CompetitionEvent).where(CompetitionEvent.external_key == item.external_key)
            )
            if event is None:
                event = CompetitionEvent(
                    external_key=item.external_key,
                    name=item.name,
                    verification_status="actionable",
                    registration_url=str(item.registration_url),
                    source_url=str(item.source_url),
                    snapshot_version=snapshot.snapshot_version,
                )
                db.add(event)
                db.flush()
            event.name = item.name
            event.verification_status = "actionable"
            event.status = CompetitionStatus.ACTIONABLE.value
            event.registration_deadline = (
                ensure_utc(item.registration_deadline) if item.registration_deadline else None
            )
            event.submission_deadline = (
                ensure_utc(item.submission_deadline) if item.submission_deadline else None
            )
            event.stages = item.stages
            event.mode = item.mode
            event.location = item.location
            event.rewards = item.rewards
            event.registration_url = str(item.registration_url)
            event.source_url = str(item.source_url)
            event.priority = item.priority
            event.tracks = item.tracks
            event.participation_mode = item.participation_mode or (
                "individual" if item.team_size_max == 1 else "team"
            )
            event.registration_mode = item.registration_mode
            event.registration_instructions = item.registration_instructions
            event.fee_note = item.fee_note
            event.recommendation_tier = item.recommendation_tier
            event.verified_at = ensure_utc(item.verified_at) if item.verified_at else None
            event.snapshot_version = snapshot.snapshot_version
            event.ingested_at = datetime.now(UTC)
            db.execute(delete(CompetitionSkill).where(CompetitionSkill.competition_id == event.id))
            for capability in skills:
                db.add(
                    CompetitionSkill(
                        competition_id=event.id,
                        capability_key=capability,
                        weight=1.0,
                    )
                )
            constraint = db.get(CompetitionConstraint, event.id)
            if constraint is None:
                constraint = CompetitionConstraint(competition_id=event.id)
                db.add(constraint)
            constraint.team_size_min = item.team_size_min
            constraint.team_size_max = item.team_size_max
            constraint.eligibility = item.eligibility
            accepted_ids.append(event.id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "snapshot_version": snapshot.snapshot_version,
        "accepted": len(accepted_ids),
        "rejected_unverified": rejected,
        "deduplicated": duplicate_count,
        "ids": accepted_ids,
    }


def ingest_snapshot_path(db: Session, path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ingest_snapshot(db, CompetitionSnapshot.model_validate(payload))


def _view(db: Session, event: CompetitionEvent) -> dict:
    skills = db.execute(
        select(CompetitionSkill, CapabilityTag)
        .join(CapabilityTag, CapabilityTag.key == CompetitionSkill.capability_key)
        .where(CompetitionSkill.competition_id == event.id)
        .order_by(CompetitionSkill.weight.desc(), CapabilityTag.label)
    ).all()
    constraint = db.get(CompetitionConstraint, event.id)
    return {
        "id": event.id,
        "name": event.name,
        "registration_deadline": (
            ensure_utc(event.registration_deadline) if event.registration_deadline else None
        ),
        "submission_deadline": (
            ensure_utc(event.submission_deadline) if event.submission_deadline else None
        ),
        "stages": event.stages,
        "mode": event.mode,
        "location": event.location,
        "rewards": event.rewards,
        "registration_url": event.registration_url,
        "source_url": event.source_url,
        "priority": event.priority,
        "tracks": event.tracks,
        "participation_mode": event.participation_mode,
        "registration_mode": event.registration_mode,
        "registration_instructions": event.registration_instructions,
        "fee_note": event.fee_note,
        **recommendation_fields(event.recommendation_tier),
        "verified_at": ensure_utc(event.verified_at) if event.verified_at else None,
        "team_forming_supported": bool(constraint and constraint.team_size_max > 1),
        "collaboration_action": (
            "official_team" if constraint and constraint.team_size_max > 1 else "prep_partner"
        ),
        "required_skills": [
            {"key": skill.capability_key, "label": tag.label, "weight": skill.weight}
            for skill, tag in skills
        ],
        "team_constraints": {
            "team_size_min": constraint.team_size_min if constraint else 1,
            "team_size_max": constraint.team_size_max if constraint else 1,
            "eligibility": constraint.eligibility if constraint else [],
        },
    }


def _apply_viewer_taste(db: Session, views: list[dict], viewer_id: str | None) -> list[dict]:
    if not viewer_id:
        return views
    from onemore.modules.taste_profile.competition_match import apply_taste_fit
    from onemore.modules.taste_profile.service import persona_dict

    return apply_taste_fit(views, persona_dict(db, viewer_id))


def list_actionable(
    db: Session,
    *,
    direction: str | None = None,
    mode: str | None = None,
    deadline_before: datetime | None = None,
    team_only: bool | None = None,
    recommendation_tier: str | None = None,
    viewer_id: str | None = None,
) -> list[dict]:
    public_snapshot = get_settings().competition_public_snapshot_version
    query = select(CompetitionEvent).where(
        CompetitionEvent.status == CompetitionStatus.ACTIONABLE.value,
        CompetitionEvent.verification_status == "actionable",
        CompetitionEvent.snapshot_version == public_snapshot,
    )
    if mode:
        query = query.where(CompetitionEvent.mode == mode)
    if deadline_before:
        query = query.where(CompetitionEvent.registration_deadline <= ensure_utc(deadline_before))
    if recommendation_tier:
        query = query.where(CompetitionEvent.recommendation_tier == recommendation_tier)
    events = list(
        db.scalars(
            query.order_by(
                CompetitionEvent.priority.desc(), CompetitionEvent.registration_deadline.asc()
            )
        )
    )
    now = datetime.now(UTC)
    events = [
        event
        for event in events
        if not event.registration_deadline or ensure_utc(event.registration_deadline) >= now
    ]
    views = [_view(db, event) for event in events]
    if direction:
        lowered = direction.lower()
        views = [
            item
            for item in views
            if any(lowered in track.lower() for track in item["tracks"])
            or any(lowered in skill["label"].lower() for skill in item["required_skills"])
        ]
    if team_only:
        views = [item for item in views if item["team_constraints"]["team_size_max"] > 1]
    return _apply_viewer_taste(db, views, viewer_id)


def list_recommendation_tiers() -> list[dict]:
    """Public catalog for filter chips; no DB read."""
    return [
        {
            "code": item.code,
            "label": item.label,
            "description": item.description,
            "sort_order": item.sort_order,
        }
        for item in recommendation_tier_catalog()
    ]


def get_actionable(
    db: Session, competition_id: str, *, viewer_id: str | None = None
) -> dict:
    public_snapshot = get_settings().competition_public_snapshot_version
    event = db.scalar(
        select(CompetitionEvent).where(
            CompetitionEvent.id == competition_id,
            CompetitionEvent.status == CompetitionStatus.ACTIONABLE.value,
            CompetitionEvent.verification_status == "actionable",
            CompetitionEvent.snapshot_version == public_snapshot,
        )
    )
    if event is None:
        raise NotFoundError("赛事", competition_id)
    if event.registration_deadline and ensure_utc(event.registration_deadline) < datetime.now(UTC):
        raise NotFoundError("可报名赛事", competition_id)
    views = _apply_viewer_taste(db, [_view(db, event)], viewer_id)
    return views[0]


def list_teams(db: Session, competition_id: str) -> list[dict]:
    """招募中的赛事队伍：经 source_intent_id 关联到赛事，只暴露匿名结构
    （规模 / 池内人数 / 角色缺口），不含任何成员身份。"""
    from onemore.db.models import Gathering, GatheringMember, GatheringStatus, IntentCard

    now = datetime.now(UTC)
    rows = list(
        db.scalars(
            select(Gathering)
            .join(IntentCard, Gathering.source_intent_id == IntentCard.id)
            .where(
                IntentCard.competition_id == competition_id,
                Gathering.status == GatheringStatus.POOLING.value,
                or_(Gathering.expires_at.is_(None), Gathering.expires_at > now),
            )
            .order_by(Gathering.created_at.desc())
        )
    )
    teams: list[dict] = []
    for gathering in rows:
        member_count = db.scalar(
            select(func.count())
            .select_from(GatheringMember)
            .where(
                GatheringMember.gathering_id == gathering.id,
                GatheringMember.left_at.is_(None),
            )
        )
        teams.append(
            {
                "id": gathering.id,
                "title": gathering.title,
                "gathering_type": gathering.gathering_type,
                "status": gathering.status,
                "location": gathering.location,
                "campus": gathering.campus,
                "start_at": gathering.start_at,
                "target_size": gathering.target_size,
                "member_count": int(member_count or 0),
                "required_roles": list(gathering.required_roles or []),
                "expires_at": gathering.expires_at,
            }
        )
    return teams


def expire_sweep(db: Session) -> int:
    now = datetime.now(UTC)
    events = list(
        db.scalars(
            select(CompetitionEvent).where(
                CompetitionEvent.status == CompetitionStatus.ACTIONABLE.value
            )
        )
    )
    expired = 0
    for event in events:
        deadline = event.registration_deadline or event.submission_deadline
        if deadline and ensure_utc(deadline) < now:
            event.status = CompetitionStatus.EXPIRED.value
            expired += 1
    db.commit()
    return expired


competition_view = _view
