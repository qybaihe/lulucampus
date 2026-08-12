from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.errors import AppError, NotFoundError
from onemore.db.models import (
    AuthorizationGrant,
    CapabilityTag,
    Course,
    Enrollment,
    Profile,
    ProfileInitStatus,
    TrustProfile,
    User,
)

COURSE_TYPE_WEIGHT = {
    "required": 1.0,
    "limited_elective": 1.2,
    "elective": 1.4,
    "cross_major": 1.8,
    "minor": 2.0,
}


def ensure_profile(db: Session, user_id: str) -> Profile:
    profile = db.get(Profile, user_id)
    if profile is None:
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.flush()
    return profile


def begin_profile_init(db: Session, user_id: str, *, force: bool = False) -> Profile:
    profile = ensure_profile(db, user_id)
    if profile.init_status == ProfileInitStatus.READY.value and not force:
        return profile
    profile.init_status = ProfileInitStatus.PROCESSING.value
    profile.init_progress = {
        "curriculum": "pending",
        "timetable": "pending",
        "capabilities": "pending",
        "cross_major": "pending",
    }
    db.commit()
    return profile


def map_course_to_domain(db: Session, course_code: str) -> tuple[str, list[str]]:
    course = db.scalar(select(Course).where(Course.code == course_code))
    if course is None:
        return "general", []
    return course.domain, list(course.capability_tags)


def init_profile(db: Session, user_id: str) -> Profile:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", user_id)
    profile = ensure_profile(db, user_id)
    profile.init_status = ProfileInitStatus.PROCESSING.value
    profile.init_progress = {
        "curriculum": "completed",
        "timetable": "processing",
        "capabilities": "pending",
        "cross_major": "pending",
    }
    db.commit()

    rows = db.execute(
        select(Enrollment, Course)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == user_id)
    ).all()
    vector: dict[str, float] = defaultdict(float)
    verified: set[str] = set()
    cross_domains: dict[str, float] = defaultdict(float)
    main_domain = _major_domain(user.major)
    for enrollment, course in rows:
        weight = COURSE_TYPE_WEIGHT.get(enrollment.course_type, 1.0)
        for tag in course.capability_tags:
            vector[tag] += weight
            verified.add(tag)
        if course.domain != main_domain and enrollment.course_type in {
            "elective",
            "cross_major",
            "minor",
        }:
            cross_domains[course.domain] += weight

    # Preserve Douyin taste scores so course ETL does not wipe interest matching.
    previous_taste = {
        key: value
        for key, value in (profile.capability_vector or {}).items()
        if str(key).startswith("taste:")
    }
    for tag in profile.self_reported_tags:
        if str(tag).startswith("taste:"):
            continue
        vector[tag] += 0.35
    for key, value in previous_taste.items():
        vector[key] = max(vector.get(key, 0.0), value)
    max_value = max(vector.values(), default=1.0)
    profile.capability_vector = {
        key: round(value / max_value, 4) for key, value in sorted(vector.items())
    }
    profile.verified_tags = sorted(verified)
    academic_domains = [
        key for key, _ in sorted(cross_domains.items(), key=lambda item: item[1], reverse=True)
    ]
    # Prefer taste interest labels when a Douyin profile exists.
    from onemore.db.models import TasteProfile

    taste = db.get(TasteProfile, user_id)
    if taste is not None and taste.interest_domains:
        taste_labels: list[str] = []
        for item in taste.interest_domains:
            if not isinstance(item, dict):
                continue
            label = item.get("label") or item.get("key")
            if label:
                taste_labels.append(str(label))
        profile.interest_domains = taste_labels[:12] if taste_labels else academic_domains
    else:
        profile.interest_domains = academic_domains
    profile.cross_major_score = round(min(1.0, sum(cross_domains.values()) / 6.0), 4)
    grants = {
        scope
        for scope in db.scalars(
            select(AuthorizationGrant.scope).where(
                AuthorizationGrant.user_id == user_id,
                AuthorizationGrant.granted.is_(True),
            )
        )
    }
    required_grants = {"curriculum", "enrollment", "timetable"}
    complete = required_grants.issubset(grants)
    profile.init_status = (
        ProfileInitStatus.READY.value if complete else ProfileInitStatus.PARTIAL.value
    )
    profile.init_progress = {
        "curriculum": "completed" if "curriculum" in grants else "authorization_required",
        "timetable": "completed" if "timetable" in grants else "authorization_required",
        "enrollment": "completed" if "enrollment" in grants else "authorization_required",
        "capabilities": "completed",
        "cross_major": "completed",
        "enrollments_found": len(rows),
        "capabilities_found": len(verified),
    }
    db.commit()
    db.refresh(profile)
    return profile


def edit_self_reported_tags(
    db: Session, user_id: str, tags: list[str], hidden_verified: list[str]
) -> Profile:
    profile = ensure_profile(db, user_id)
    known = set(db.scalars(select(CapabilityTag.key)))
    # Preserve Douyin taste tags (namespaced). Clients usually only send catalog
    # keys; re-attach taste:* keys that were already synced from the import.
    existing_taste = {
        key for key in (profile.self_reported_tags or []) if str(key).startswith("taste:")
    }
    requested = set(tags)
    unknown = sorted(
        key
        for key in requested
        if key not in known and not str(key).startswith("taste:")
    )
    if unknown:
        raise AppError(
            "UNKNOWN_CAPABILITY_TAG",
            "存在未注册的能力标签",
            422,
            {"unknown": unknown},
        )
    if not set(hidden_verified).issubset(set(profile.verified_tags)):
        raise AppError("INVALID_VERIFIED_TAG", "只能隐藏已验证标签，不能伪造", 422)
    kept_taste = {key for key in requested if str(key).startswith("taste:")} or existing_taste
    catalog = {key for key in requested if not str(key).startswith("taste:")}
    profile.self_reported_tags = sorted(catalog | kept_taste)
    profile.hidden_verified_tags = sorted(set(hidden_verified))
    db.commit()
    return init_profile(db, user_id)


def get_profile_data(db: Session, user_id: str) -> tuple[User, Profile, TrustProfile | None]:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", user_id)
    return user, ensure_profile(db, user_id), db.get(TrustProfile, user_id)


def _major_domain(major: str | None) -> str:
    value = (major or "").lower()
    if any(word in value for word in ("软件", "计算机", "人工智能", "computer", "software")):
        return "computer_science"
    if any(word in value for word in ("设计", "design")):
        return "design"
    if any(word in value for word in ("经济", "管理", "商", "business")):
        return "business"
    if any(word in value for word in ("生物", "医学", "bio")):
        return "biomedicine"
    return "general"
