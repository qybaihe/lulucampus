from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.db.models import (
    Assignment,
    AuthorizationGrant,
    CapabilityTag,
    ConfirmationStatus,
    Course,
    Enrollment,
    ExternalEvent,
    Gathering,
    GatheringMember,
    GatheringStatus,
    GrantScope,
    Profile,
    ProfileInitStatus,
    TimeWindow,
    TrustLevel,
    TrustProfile,
    User,
)
from onemore.modules.competitions.service import ingest_snapshot_path

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


def seed_demo_data(db: Session, root: Path | None = None) -> None:
    seed_reference_data(db)
    now = datetime.now(UTC)
    user_specs = [
        ("u_demo_1", "小岚", "软件工程", "F", ["SE1001", "CS2002", "DS3001"]),
        ("u_demo_2", "阿衡", "计算机科学", "M", ["CS2002", "FE1001"]),
        ("u_demo_3", "知夏", "传播设计", "F", ["DS3001", "BA2001"]),
        ("u_demo_4", "庭川", "工商管理", "M", ["BA2001", "SE1001"]),
    ]
    for index, (user_id, display_name, major, gender_code, course_codes) in enumerate(user_specs):
        user = db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                netid_hash=f"demo-hash-{index}",
                display_name=display_name,
                college="示范学院",
                major=major,
                grade_year=2024,
                campus="珠海校区",
                gender_code=gender_code,
                verified_at=now - timedelta(days=60),
                social_enabled=True,
            )
            db.add(user)
            db.flush()
        elif user.gender_code is None:
            user.gender_code = gender_code
        for scope in GrantScope:
            grant = db.scalar(
                select(AuthorizationGrant).where(
                    AuthorizationGrant.user_id == user_id,
                    AuthorizationGrant.scope == scope.value,
                )
            )
            if grant is None:
                db.add(
                    AuthorizationGrant(
                        user_id=user_id,
                        scope=scope.value,
                        granted=True,
                        granted_at=now,
                    )
                )
        trust = db.get(TrustProfile, user_id)
        if trust is None:
            db.add(
                TrustProfile(
                    user_id=user_id,
                    level=TrustLevel.T2.value,
                    completed_gatherings=3,
                    on_time_confirm_rate=1.0,
                )
            )
        for code in course_codes:
            course = db.scalar(select(Course).where(Course.code == code))
            if course is None:
                continue
            exists = db.scalar(
                select(Enrollment).where(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id == course.id,
                    Enrollment.class_code == f"{code}-01",
                    Enrollment.term == "2026-fall",
                )
            )
            if exists is None:
                start = (now + timedelta(days=1)).replace(
                    hour=9 + index, minute=0, second=0, microsecond=0
                )
                db.add(
                    Enrollment(
                        user_id=user_id,
                        course_id=course.id,
                        class_code=f"{code}-01",
                        term="2026-fall",
                        status="current",
                        course_type=course.course_type,
                        meeting_windows=[
                            {
                                "week": max(1, int(now.strftime("%W")) % 25),
                                "start_at": start.isoformat(),
                                "end_at": (start + timedelta(hours=2)).isoformat(),
                                "location": "珠海校区教学楼",
                            }
                        ],
                    )
                )
        if db.get(Profile, user_id) is None:
            db.add(
                Profile(
                    user_id=user_id,
                    init_status=ProfileInitStatus.NOT_STARTED.value,
                    self_reported_tags=[],
                )
            )
        if not db.scalar(select(TimeWindow.id).where(TimeWindow.user_id == user_id)):
            for offset in range(1, 8):
                start = (now + timedelta(days=offset)).replace(
                    hour=19 if offset < 6 else 14, minute=0, second=0, microsecond=0
                )
                db.add(
                    TimeWindow(
                        user_id=user_id,
                        start_at=start,
                        end_at=start + timedelta(hours=3),
                        campus="珠海校区",
                        recurring=True,
                        stability=0.95 - index * 0.02,
                    )
                )
    db.commit()

    from onemore.modules.profile.service import init_profile

    for user_id, *_ in user_specs:
        init_profile(db, user_id)
    demo_gatherings: list[Gathering] = []
    for number in range(1, 4):
        gathering = db.scalar(select(Gathering).where(Gathering.title == f"演示共同经历 {number}"))
        if gathering is None:
            gathering = Gathering(
                gathering_type="DDL冲刺" if number < 3 else "羽毛球",
                mode="similar",
                title=f"演示共同经历 {number}",
                goal="完成一次真实的共同任务",
                status=GatheringStatus.COMPLETED.value,
                min_size=3,
                target_size=4,
                required_trust_level="T1",
                campus="珠海校区",
                start_at=now - timedelta(days=number * 7, hours=2),
                end_at=now - timedelta(days=number * 7),
                completed_at=now - timedelta(days=number * 7),
            )
            db.add(gathering)
            db.flush()
            for member_index, (user_id, *_rest) in enumerate(user_specs):
                if gathering.start_at is None:
                    continue
                db.add(
                    GatheringMember(
                        gathering_id=gathering.id,
                        user_id=user_id,
                        role="participant",
                        confirmation_status=ConfirmationStatus.CONFIRMED.value,
                        joined_via="owner" if member_index == number % 4 else "matching",
                        confirmed_at=gathering.start_at - timedelta(hours=24),
                        completion_confirmed=True,
                    )
                )
        demo_gatherings.append(gathering)
    db.commit()
    from onemore.modules.collab.service import record_experience

    for gathering in demo_gatherings:
        record_experience(db, gathering.id)
    db.commit()
    if not db.scalar(select(Assignment.id).where(Assignment.user_id == "u_demo_1")):
        course = db.scalar(select(Course).where(Course.code == "SE1001"))
        if course is None:
            raise RuntimeError("seed reference course SE1001 is missing")
        db.add(
            Assignment(
                user_id="u_demo_1",
                course_id=course.id,
                title="软件工程迭代作业",
                due_at=now + timedelta(hours=20),
                status="unfinished",
                source_ref="demo-assignment-1",
            )
        )
    if not db.scalar(select(ExternalEvent.id)):
        db.add_all(
            [
                ExternalEvent(
                    source="teachin",
                    external_key="demo-teachin-1",
                    title="科技企业校园宣讲会",
                    starts_at=now + timedelta(days=3),
                    ends_at=now + timedelta(days=3, hours=2),
                    location="珠海校区报告厅",
                    official_url="https://example.edu.cn/events/teachin-1",
                    details={"registration": "official_link_only"},
                ),
                ExternalEvent(
                    source="seminar",
                    external_key="demo-seminar-1",
                    title="可信人工智能前沿讲座",
                    starts_at=now + timedelta(days=5),
                    ends_at=now + timedelta(days=5, hours=2),
                    location="珠海校区学术交流中心",
                    official_url="https://example.edu.cn/events/seminar-1",
                    details={"registration": "official_link_only"},
                ),
            ]
        )
    db.commit()
    # Demo users need realistic content, but the public competition catalogue must
    # never be populated from the small demo fixture.  Keep demo people/gatherings
    # while seeding the same reviewed production snapshot used by clients.
    fixture = (root or Path.cwd()) / "fixtures/competition_snapshot_2026-08-11_v1.1.json"
    if fixture.exists():
        ingest_snapshot_path(db, fixture)
