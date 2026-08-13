from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.db.demo_cast import (
    CAST_BY_ID,
    CAST_PASSWORD_HASH,
    CAST_TASTE,
    CAST_USERS,
    COMPLETED_GATHERINGS,
    COURSE_MEETINGS,
    EXTERNAL_EVENTS,
    EXTRA_COURSES,
    OPEN_GATHERINGS,
    CastGathering,
)
from onemore.db.models import (
    Assignment,
    AuthorizationGrant,
    CapabilityTag,
    CompetitionEvent,
    Course,
    Enrollment,
    ExternalEvent,
    Gathering,
    GatheringMember,
    GatheringStatus,
    GrantScope,
    IntentCard,
    IntentStatus,
    Message,
    Profile,
    ProfileInitStatus,
    SessionHealth,
    TasteImportSession,
    TimeWindow,
    TrustProfile,
    User,
)
from onemore.modules.competitions.service import ingest_snapshot_path

_SHANGHAI = ZoneInfo("Asia/Shanghai")

CAPABILITY_TAGS = [
    ("backend", "后端开发", "computer_science"),
    ("frontend", "前端开发", "computer_science"),
    ("machine_learning", "机器学习", "computer_science"),
    ("data_analysis", "数据分析", "computer_science"),
    ("product", "产品设计", "business"),
    ("visual_design", "视觉设计", "design"),
    ("design", "交互设计", "design"),
    ("business_analysis", "商业分析", "business"),
    ("operations", "活动运营", "communication"),
]


def seed_reference_data(db: Session) -> None:
    for key, label, domain in CAPABILITY_TAGS:
        if db.get(CapabilityTag, key) is None:
            db.add(CapabilityTag(key=key, label=label, domain=domain))
    courses = [
        ("SE1001", "软件工程", "computer_science", ["backend", "product"], "required"),
        (
            "CS2002",
            "机器学习",
            "computer_science",
            ["machine_learning", "data_analysis"],
            "limited_elective",
        ),
        ("DS3001", "视觉传达设计", "design", ["visual_design", "design"], "cross_major"),
        ("BA2001", "商业模式设计", "business", ["business_analysis", "product"], "elective"),
        ("FE1001", "Web 前端开发", "computer_science", ["frontend"], "elective"),
        *EXTRA_COURSES,
    ]
    for code, name, domain, tags, course_type in courses:
        existing = db.scalar(select(Course).where(Course.code == code))
        if existing is None:
            db.add(
                Course(
                    code=code,
                    name=name,
                    domain=domain,
                    capability_tags=tags,
                    course_type=course_type,
                )
            )
    db.commit()


def _as_shanghai(now: datetime) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(_SHANGHAI)


def _next_weekday(now: datetime, weekday: int, hour: int) -> datetime:
    local = _as_shanghai(now)
    days = (weekday - local.weekday()) % 7
    candidate = (local + timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    if candidate <= local:
        candidate += timedelta(days=7)
    return candidate


def _gathering_bounds(spec: CastGathering, now: datetime) -> tuple[datetime, datetime]:
    local_now = _as_shanghai(now)
    if spec.start_days_ago is not None:
        start_local = (local_now - timedelta(days=spec.start_days_ago)).replace(
            hour=spec.start_hour, minute=0, second=0, microsecond=0
        )
    elif spec.start_weekday is not None:
        start_local = _next_weekday(local_now, spec.start_weekday, spec.start_hour)
    else:
        start_local = (local_now + timedelta(days=2)).replace(
            hour=spec.start_hour, minute=0, second=0, microsecond=0
        )
    start = start_local.astimezone(UTC)
    return start, start + timedelta(hours=spec.duration_hours)


def _ensure_session_health(db: Session, user_id: str, now: datetime) -> None:
    for subsystem in ("cas", "jwxt", "libic", "gym", "explore"):
        health = db.scalar(
            select(SessionHealth).where(
                SessionHealth.user_id == user_id,
                SessionHealth.subsystem == subsystem,
            )
        )
        if health is None:
            health = SessionHealth(user_id=user_id, subsystem=subsystem)
            db.add(health)
        health.healthy = True
        health.last_checked_at = now
        health.error_category = None


def _seed_users(db: Session, now: datetime) -> None:
    for spec in CAST_USERS:
        user = db.get(User, spec.id)
        if user is None:
            user = User(id=spec.id, netid_hash=f"demo-hash-{spec.netid_index}")
            db.add(user)
            db.flush()
        user.display_name = spec.display_name
        user.college = spec.college
        user.major = spec.major
        user.grade_year = spec.grade_year
        user.campus = spec.campus
        user.gender_code = spec.gender_code
        user.verified_at = user.verified_at or now - timedelta(days=60)
        user.social_enabled = True
        user.course_matching_enabled = True
        user.account_status = "active"
        user.identity_disclosure = spec.identity_disclosure
        user.minimum_group_size = spec.minimum_group_size
        user.matching_preferences = {
            "interaction_style": spec.interaction_style,
            "sport_level": spec.sport_level,
            "study_intensity": spec.study_intensity,
        }
        if user.phone is None:
            taken = db.scalar(select(User.id).where(User.phone == spec.phone))
            if taken is None:
                user.phone = spec.phone
                user.password_hash = CAST_PASSWORD_HASH
        for scope in GrantScope:
            grant = db.scalar(
                select(AuthorizationGrant).where(
                    AuthorizationGrant.user_id == spec.id,
                    AuthorizationGrant.scope == scope.value,
                )
            )
            if grant is None:
                db.add(
                    AuthorizationGrant(
                        user_id=spec.id,
                        scope=scope.value,
                        granted=True,
                        granted_at=now,
                    )
                )
            else:
                grant.granted = True
                grant.granted_at = grant.granted_at or now
                grant.revoked_at = None
        trust = db.get(TrustProfile, spec.id)
        if trust is None:
            trust = TrustProfile(user_id=spec.id)
            db.add(trust)
        trust.level = spec.trust_level
        trust.completed_gatherings = spec.completed_gatherings
        trust.initiated_gatherings = spec.initiated_gatherings
        trust.recurrences = spec.recurrences
        trust.on_time_confirm_rate = spec.on_time_confirm_rate
        _ensure_session_health(db, spec.id, now)
        if db.get(Profile, spec.id) is None:
            db.add(
                Profile(
                    user_id=spec.id,
                    init_status=ProfileInitStatus.NOT_STARTED.value,
                    self_reported_tags=[],
                )
            )
        for code in spec.course_codes:
            course = db.scalar(select(Course).where(Course.code == code))
            if course is None:
                continue
            class_code = f"{code}-01"
            exists = db.scalar(
                select(Enrollment).where(
                    Enrollment.user_id == spec.id,
                    Enrollment.course_id == course.id,
                    Enrollment.class_code == class_code,
                    Enrollment.term == "2026-fall",
                )
            )
            if exists is None:
                location, hour = COURSE_MEETINGS.get(code, (f"{spec.campus}教学楼", 10))
                start = (now + timedelta(days=1)).replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
                db.add(
                    Enrollment(
                        user_id=spec.id,
                        course_id=course.id,
                        class_code=class_code,
                        term="2026-fall",
                        status="current",
                        course_type=course.course_type,
                        meeting_windows=[
                            {
                                "week": max(1, int(now.strftime("%W")) % 25),
                                "start_at": start.isoformat(),
                                "end_at": (start + timedelta(hours=2)).isoformat(),
                                "location": location,
                            }
                        ],
                    )
                )
        if not db.scalar(select(TimeWindow.id).where(TimeWindow.user_id == spec.id)):
            for offset in range(1, 8):
                start = (now + timedelta(days=offset)).replace(
                    hour=19 if offset < 6 else 14, minute=0, second=0, microsecond=0
                )
                db.add(
                    TimeWindow(
                        user_id=spec.id,
                        start_at=start,
                        end_at=start + timedelta(hours=3),
                        campus=spec.campus,
                        recurring=True,
                        stability=0.95 - spec.netid_index * 0.02,
                    )
                )
    db.commit()


def _seed_taste(db: Session, now: datetime) -> None:
    from onemore.modules.taste_profile import service as taste_service

    for user_id, result in CAST_TASTE.items():
        import_id = f"imp_cast_{user_id}"
        session = db.get(TasteImportSession, import_id)
        if session is None:
            session = TasteImportSession(
                id=import_id,
                user_id=user_id,
                status=taste_service.READY,
                expires_at=now + timedelta(days=30),
            )
            db.add(session)
        session.status = taste_service.READY
        session.authenticated_at = session.authenticated_at or now
        session.completed_at = now
        spec = CAST_BY_ID.get(user_id)
        session.source_profile = {
            "nickname": spec.display_name if spec else user_id,
            "avatar_url": None,
            "uid": f"cast-{user_id}",
        }
        sample = result.get("sample") or {}
        session.progress = {
            "phase": "ready",
            "current": sample.get("items") or 0,
            "total": sample.get("items") or 0,
            "percent": 100.0,
            "message": "画像已生成",
        }
        session.collection_summary = {
            "api_pages": 3,
            "items_collected": sample.get("items") or 0,
            "has_more": False,
        }
        session.questions = []
        session.result_snapshot = taste_service.normalize_taste_result(result) or result
        taste_service.upsert_taste_profile(db, session, result)
    db.commit()


def _attach_competition_id(db: Session, metadata: dict) -> dict:
    """把 competition_name 解析成当前快照里的赛事 id，方便 /competitions/{id}/teams 关联。"""
    name = metadata.get("competition_name")
    if not name or metadata.get("competition_id"):
        return dict(metadata)
    event = db.scalar(select(CompetitionEvent).where(CompetitionEvent.name == name))
    if event is None:
        return dict(metadata)
    attached = dict(metadata)
    attached["competition_id"] = event.id
    return attached


def _seed_gathering(db: Session, spec: CastGathering, now: datetime) -> Gathering:
    gathering = db.scalar(select(Gathering).where(Gathering.title == spec.title))
    start_at, end_at = _gathering_bounds(spec, now)
    created = gathering is None
    metadata = _attach_competition_id(db, dict(spec.official_metadata))
    if gathering is None:
        intent = None
        # Pooling gap cards must not enter the matching pool, or test runs
        # will absorb them. Mood notes stay on completed / non-pooling intents.
        if spec.mood_note and spec.status != GatheringStatus.POOLING.value:
            intent = IntentCard(
                user_id=spec.owner_user_id,
                status=IntentStatus.MATCHED.value,
                gathering_type=spec.gathering_type,
                mode=spec.mode,
                goal=spec.goal,
                mood_note=spec.mood_note,
                required_roles=list(spec.required_roles),
                campus=spec.campus,
                min_size=spec.min_size,
                target_size=spec.target_size,
                expires_at=now + timedelta(days=7),
            )
            db.add(intent)
            db.flush()
        gathering = Gathering(
            source_intent_id=intent.id if intent else None,
            owner_user_id=spec.owner_user_id,
            gathering_type=spec.gathering_type,
            mode=spec.mode,
            title=spec.title,
            goal=spec.goal,
            status=spec.status,
            min_size=spec.min_size,
            target_size=spec.target_size,
            required_trust_level=spec.required_trust_level,
            campus=spec.campus,
            identity_disclosure=spec.identity_disclosure,
            start_at=start_at,
            end_at=end_at,
            location=spec.location,
            required_roles=list(spec.required_roles),
            official_metadata=metadata,
            expires_at=(
                None
                if spec.status == GatheringStatus.COMPLETED.value
                else now + timedelta(days=7)
            ),
            completed_at=end_at if spec.status == GatheringStatus.COMPLETED.value else None,
        )
        db.add(gathering)
        db.flush()
        for member in spec.members:
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=member.user_id,
                    role=member.role,
                    confirmation_status=member.confirmation,
                    joined_via=member.joined_via,
                    confirmed_at=start_at - timedelta(hours=24),
                    completion_confirmed=spec.status == GatheringStatus.COMPLETED.value,
                )
            )
    else:
        gathering.start_at = start_at
        gathering.end_at = end_at
        gathering.location = spec.location
        gathering.required_roles = list(spec.required_roles)
        if spec.status == GatheringStatus.POOLING.value and gathering.status == GatheringStatus.POOLING.value:
            gathering.status = spec.status
            gathering.expires_at = now + timedelta(days=7)
            gathering.official_metadata = metadata
    db.flush()
    if created and spec.messages and spec.status == GatheringStatus.COMPLETED.value:
        from onemore.modules.collab.service import open_gathering_channel

        channel = open_gathering_channel(db, gathering.id)
        existing = db.scalar(select(Message.id).where(Message.channel_id == channel.id))
        if existing is None:
            sent = start_at + timedelta(minutes=10)
            for user_id, content in spec.messages:
                db.add(
                    Message(
                        channel_id=channel.id,
                        sender_id=user_id,
                        sender_type="human",
                        content_type="text",
                        content=content,
                        sent_at=sent,
                    )
                )
                sent += timedelta(minutes=4)
    return gathering


def seed_demo_data(db: Session, root: Path | None = None) -> None:
    seed_reference_data(db)
    now = datetime.now(UTC)
    _seed_users(db, now)

    from onemore.modules.profile.service import init_profile

    for spec in CAST_USERS:
        init_profile(db, spec.id)
    _seed_taste(db, now)
    from onemore.db.peer_overlap import attach_live_test_users, seed_cast_gym_slots

    seed_cast_gym_slots(db)
    attach_live_test_users(db)

    completed: list[Gathering] = []
    for spec in COMPLETED_GATHERINGS:
        completed.append(_seed_gathering(db, spec, now))
    db.commit()
    from onemore.modules.collab.service import record_experience
    from onemore.modules.trust.service import recompute_level

    for gathering in completed:
        record_experience(db, gathering.id)
    db.commit()

    for spec in OPEN_GATHERINGS:
        _seed_gathering(db, spec, now)
    db.commit()

    for spec in CAST_USERS:
        recompute_level(db, spec.id)
        trust = db.get(TrustProfile, spec.id)
        if trust is not None:
            # Keep the narrative trust floor (T3 局主等)；次数以真实成局记录为准。
            trust.level = spec.trust_level
            trust.on_time_confirm_rate = spec.on_time_confirm_rate
    db.commit()

    for spec in CAST_USERS:
        if spec.assignment is None:
            continue
        if db.scalar(select(Assignment.id).where(Assignment.user_id == spec.id)):
            continue
        code, title = spec.assignment
        course = db.scalar(select(Course).where(Course.code == code))
        if course is None:
            continue
        db.add(
            Assignment(
                user_id=spec.id,
                course_id=course.id,
                title=title,
                due_at=now + timedelta(hours=20 + spec.netid_index),
                status="unfinished",
                source_ref=f"cast-assignment-{spec.id}",
            )
        )

    for event in EXTERNAL_EVENTS:
        starts_at = now + timedelta(days=event["days"])
        ends_at = starts_at + timedelta(hours=2)
        existing = db.scalar(
            select(ExternalEvent).where(ExternalEvent.external_key == event["external_key"])
        )
        if existing is None:
            db.add(
                ExternalEvent(
                    source=event["source"],
                    external_key=event["external_key"],
                    title=event["title"],
                    starts_at=starts_at,
                    ends_at=ends_at,
                    location=event["location"],
                    official_url=event["official_url"],
                    details=event["details"],
                )
            )
            continue
        existing.source = event["source"]
        existing.title = event["title"]
        existing.starts_at = starts_at
        existing.ends_at = ends_at
        existing.location = event["location"]
        existing.official_url = event["official_url"]
        existing.details = event["details"]
    db.commit()
    fixture = (root or Path.cwd()) / "fixtures/competition_snapshot_2026-08-11_v1.1.json"
    if fixture.exists():
        ingest_snapshot_path(db, fixture)
