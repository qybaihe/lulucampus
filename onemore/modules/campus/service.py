from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.errors import NotFoundError
from onemore.core.time import ensure_utc
from onemore.db.models import (
    ActionStatus,
    Assignment,
    CampusAction,
    Course,
    Enrollment,
    ExternalEvent,
    Gathering,
    GatheringMember,
    GatheringStatus,
    SceneTrigger,
    User,
    utcnow,
)
from onemore.hermes.catalog import CATALOG
from onemore.hermes.schemas import ActionName
from onemore.modules.actions import service as action_service
from onemore.modules.campus.schemas import CampusEventCreateRequest, PublicEventView
from onemore.modules.trust import service as trust_service
from onemore.modules.schedule import service as schedule_service


def list_assignments(db: Session, user_id: str, status: str) -> list[dict]:
    query = select(Assignment).where(Assignment.user_id == user_id)
    if status:
        query = query.where(Assignment.status == status)
    return [
        {
            "id": item.id,
            "course_id": item.course_id,
            "title": item.title,
            "due_at": ensure_utc(item.due_at),
            "status": item.status,
        }
        for item in db.scalars(query.order_by(Assignment.due_at))
    ]


def assignment_detail(db: Session, user_id: str, assignment_id: str) -> dict:
    item = db.scalar(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.user_id == user_id,
        )
    )
    if item is None:
        raise NotFoundError("作业", assignment_id)
    course = db.get(Course, item.course_id) if item.course_id else None
    return {
        "id": item.id,
        "title": item.title,
        "due_at": ensure_utc(item.due_at),
        "status": item.status,
        "course": ({"id": course.id, "code": course.code, "name": course.name} if course else None),
        "source_ref": item.source_ref,
    }


def course_detail(db: Session, user_id: str, course_id: str) -> dict:
    row = db.execute(
        select(Course, Enrollment)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Course.id == course_id, Enrollment.user_id == user_id)
    ).first()
    if row is None:
        raise NotFoundError("课程", course_id)
    course, enrollment = row
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "domain": course.domain,
        "capability_tags": course.capability_tags,
        "class_code": enrollment.class_code,
        "term": enrollment.term,
        "meeting_windows": enrollment.meeting_windows,
        "privacy": "only_current_user_enrollment",
    }


def list_events(
    db: Session, event_type: str | None = None, start: date | None = None
) -> list[PublicEventView]:
    query = select(ExternalEvent)
    if event_type:
        query = query.where(ExternalEvent.source == event_type)
    if start:
        start_dt = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
        query = query.where(ExternalEvent.starts_at >= start_dt)
    return [
        PublicEventView(
            id=item.id,
            type=item.source,
            title=item.title,
            starts_at=ensure_utc(item.starts_at) if item.starts_at else None,
            ends_at=ensure_utc(item.ends_at) if item.ends_at else None,
            location=item.location,
            official_url=item.official_url,
            details=item.details,
        )
        for item in db.scalars(
            query.order_by(ExternalEvent.starts_at.asc().nulls_last()).limit(100)
        )
    ]


def event_detail(db: Session, event_id: str) -> PublicEventView:
    item = db.get(ExternalEvent, event_id)
    if item is None:
        raise NotFoundError("活动", event_id)
    return PublicEventView(
        id=item.id,
        type=item.source,
        title=item.title,
        starts_at=ensure_utc(item.starts_at) if item.starts_at else None,
        ends_at=ensure_utc(item.ends_at) if item.ends_at else None,
        location=item.location,
        official_url=item.official_url,
        details=item.details,
    )


def create_user_event(
    db: Session, user_id: str, body: CampusEventCreateRequest
) -> PublicEventView:
    """用户发布校园活动：T4 能力门槛，列表中匿名呈现（不暴露发布者身份）。"""
    trust_service.require_unlock(db, user_id, "campus_event_publish")
    item = ExternalEvent(
        source=body.type,
        external_key=f"user:{user_id}:{uuid4().hex}",
        title=body.title,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        location=body.location,
        official_url=body.official_url or "",
        details={
            "publisher": "user",
            **({"description": body.description} if body.description else {}),
        },
    )
    db.add(item)
    db.flush()
    db.commit()
    return PublicEventView(
        id=item.id,
        type=item.source,
        title=item.title,
        starts_at=ensure_utc(item.starts_at) if item.starts_at else None,
        ends_at=ensure_utc(item.ends_at) if item.ends_at else None,
        location=item.location,
        official_url=item.official_url or None,
        details=item.details,
    )


def _scene_trigger(db: Session, user_id: str) -> dict | None:
    due = db.scalar(
        select(Assignment).where(
            Assignment.user_id == user_id,
            Assignment.status == "unfinished",
            Assignment.due_at <= datetime.now(UTC) + timedelta(hours=36),
            Assignment.due_at > datetime.now(UTC),
        )
    )
    if due is None:
        return None
    key = f"assignment:{due.id}"
    record = db.scalar(
        select(SceneTrigger).where(SceneTrigger.user_id == user_id, SceneTrigger.scene_key == key)
    )
    if record is None:
        record = SceneTrigger(user_id=user_id, scene_key=key)
        db.add(record)
    if record.disabled:
        return None
    if record.last_shown_at and ensure_utc(record.last_shown_at) > datetime.now(UTC) - timedelta(
        days=3
    ):
        return None
    record.last_shown_at = utcnow()
    db.flush()
    return {
        "scene_key": key,
        "kind": "ddl_sprint",
        "text": "今晚开一个 90 分钟冲刺局吗？",
        "context": {"assignment_id": due.id, "title": due.title},
    }


def ignore_scene_trigger(db: Session, user_id: str, scene_key: str) -> dict:
    record = db.scalar(
        select(SceneTrigger).where(
            SceneTrigger.user_id == user_id, SceneTrigger.scene_key == scene_key
        )
    )
    if record is None:
        record = SceneTrigger(user_id=user_id, scene_key=scene_key)
        db.add(record)
    record.ignored_count += 1
    if record.ignored_count >= 2:
        record.disabled = True
    db.commit()
    return {
        "scene_key": scene_key,
        "ignored_count": record.ignored_count,
        "disabled": record.disabled,
    }


def _local_day_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Asia/Shanghai calendar day in UTC [start, end)."""

    from zoneinfo import ZoneInfo

    shanghai = ZoneInfo("Asia/Shanghai")
    local = (now or datetime.now(UTC)).astimezone(shanghai)
    start = datetime.combine(local.date(), datetime.min.time(), shanghai).astimezone(UTC)
    return start, start + timedelta(days=1)


def today_summary(db: Session, user: User) -> dict:
    now = datetime.now(UTC)
    day_start, day_end = _local_day_bounds(now)
    # Only occurrences that actually fall on "today" — never dump the whole week.
    timetable = schedule_service.timetable_entries_for_day(db, user.id, now)
    pending = list(
        db.scalars(
            select(Gathering)
            .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
            .where(
                GatheringMember.user_id == user.id,
                GatheringMember.left_at.is_(None),
                Gathering.status.in_(
                    [GatheringStatus.TENTATIVE.value, GatheringStatus.PREVIEWED.value]
                ),
            )
        )
    )
    actions = list(
        db.scalars(
            select(CampusAction).where(
                CampusAction.user_id == user.id,
                CampusAction.status == ActionStatus.PREVIEWED.value,
            )
        )
    )
    # Gatherings/activities scheduled for today (confirmed and in-progress).
    active_today = list(
        db.scalars(
            select(Gathering)
            .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
            .where(
                GatheringMember.user_id == user.id,
                GatheringMember.left_at.is_(None),
                Gathering.status.in_(
                    [
                        GatheringStatus.CONFIRMED.value,
                        GatheringStatus.PREVIEWED.value,
                        GatheringStatus.EXECUTED.value,
                        GatheringStatus.ACTIVE.value,
                    ]
                ),
                Gathering.start_at >= day_start,
                Gathering.start_at < day_end,
            )
        )
    )
    assignments_today = list(
        db.scalars(
            select(Assignment).where(
                Assignment.user_id == user.id,
                Assignment.status == "unfinished",
                Assignment.due_at >= day_start,
                Assignment.due_at < day_end,
            )
        )
    )
    trigger = _scene_trigger(db, user.id)
    db.commit()

    timeline: list[dict] = []
    for item in timetable:
        timeline.append(
            {
                "kind": "course",
                "id": f"course:{item['course_id']}:{item['start_at'].isoformat()}",
                "title": item["course_name"],
                "subtitle": item.get("location"),
                "time_label": item.get("time_label"),
                "course_id": item["course_id"],
                "course_name": item["course_name"],
                "start_at": item["start_at"],
                "end_at": item["end_at"],
                "location": item.get("location"),
                "changed": item.get("changed", False),
                # Do not surface jwxt hashes / long teaching-class ids on the home timeline.
                "course_code": item.get("display_code"),
                "class_code": item.get("display_class_code"),
            }
        )
    for item in active_today:
        start_at = ensure_utc(item.start_at) if item.start_at else None
        end_at = ensure_utc(item.end_at) if item.end_at else None
        time_label = None
        if start_at is not None:
            time_label = schedule_service._time_label(start_at, end_at)
        timeline.append(
            {
                "kind": "gathering",
                "id": item.id,
                "gathering_id": item.id,
                "title": item.title,
                "subtitle": item.location,
                "time_label": time_label,
                # 输出必须带时区：iOS 端 ISO8601 解码拒绝 naive 时间。
                "start_at": start_at,
                "end_at": end_at,
                "location": item.location,
            }
        )
    for item in assignments_today:
        due_at = ensure_utc(item.due_at)
        timeline.append(
            {
                "kind": "assignment",
                "id": item.id,
                "title": item.title,
                "subtitle": "今日截止",
                "time_label": schedule_service._time_label(due_at),
                "start_at": due_at,
                "end_at": None,
                "location": None,
                "course_id": item.course_id,
            }
        )
    timeline.sort(
        key=lambda row: ensure_utc(row["start_at"])
        if row.get("start_at") is not None
        else datetime.max.replace(tzinfo=UTC)
    )

    return {
        "pending": [
            {
                "gathering_id": item.id,
                "type": "confirmation"
                if item.status == GatheringStatus.TENTATIVE.value
                else "authorization",
                "deep_link": f"onemore://gathering/{item.id}",
                "title": item.title,
                "from_name": _pending_from_name(db, item.id, user.id),
            }
            for item in pending
        ]
        + [
            {
                "action_id": item.id,
                "type": "authorization",
                "deep_link": f"onemore://action/{item.id}",
            }
            for item in actions
        ],
        "timeline": timeline,
        "scene_trigger": trigger,
        "generated_at": now,
    }


def _pending_from_name(db: Session, gathering_id: str, viewer_id: str) -> str | None:
    """待确认卡片上展示的对方称呼：优先局主，其次已确认成员。"""
    members = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
                GatheringMember.user_id != viewer_id,
            )
        )
    )
    preferred = next((m for m in members if m.joined_via == "owner"), None)
    if preferred is None:
        preferred = next(
            (m for m in members if m.confirmation_status == "confirmed"),
            members[0] if members else None,
        )
    if preferred is None:
        return None
    peer = db.get(User, preferred.user_id)
    name = (peer.display_name if peer else None) or ""
    return name.strip() or None


def compile_hermes_question(text: str, context: dict) -> tuple[ActionName | None, dict, str, bool]:
    from onemore.modules.campus.elective_hermes import is_elective_match_question

    if is_elective_match_question(text):
        # Handled as a composite Hermes path (taste + JWXT list), not a single CLI action.
        return None, {"_elective_match": True, **context}, "elective_match", False

    lowered = text.lower()
    gym_words = ("场馆", "体育馆", "羽毛球", "健身", "游泳", "网球", "乒乓球", "篮球", "排球")
    if any(word in lowered for word in ("预约", "预订", "订一个", "帮我订")):
        if "研讨室" in text:
            return ActionName.ROOM_RESERVE_PREVIEW, context, "action_preview", True
        if any(word in text for word in gym_words):
            return ActionName.GYM_BOOK_PREVIEW, context, "action_preview", True
    if any(
        word in text
        for word in (
            "今天的课",
            "今天有什么课",
            "今天有什么课程",
            "今日课程",
            "今天上什么",
        )
    ):
        return ActionName.TIMETABLE_TODAY, {}, "course_list", False
    if any(word in lowered for word in ("作业", "ddl")):
        return ActionName.ASSIGNMENT_LIST_UNFINISHED, {}, "assignment_list", False
    if "研讨室" in text:
        return ActionName.ROOM_AVAILABLE, context, "room_slots", False
    if any(word in text for word in gym_words):
        return ActionName.GYM_AVAILABLE, context, "gym_slots", False
    if any(word in text for word in ("讲座", "组会", "课题")):
        return ActionName.SEMINAR_LIST, context, "event_list", False
    if any(word in text for word in ("宣讲会", "招聘会")):
        action = (
            ActionName.CAREER_JOBFAIR_LIST if "招聘会" in text else ActionName.CAREER_TEACHIN_LIST
        )
        return action, context, "event_list", False
    if "班车" in text:
        return ActionName.TRANSIT_BUS, context, "transit_list", False
    if any(word in lowered for word in ("岐关", "qg")):
        return ActionName.TRANSIT_QIGUAN, context, "transit_list", False
    return None, {}, "capability_help", False


def hermes_ask(db: Session, user_id: str, text: str, context: dict) -> dict:
    action, params, card_type, preview = compile_hermes_question(text, context)
    if action is None and params.get("_elective_match"):
        from onemore.modules.campus.elective_hermes import answer_elective_match

        data = answer_elective_match(db, user_id, text, params)
        return {
            "kind": "result",
            "action": "elective.match_taste",
            "card_type": "elective_match",
            "data": data,
            "requires_preview": False,
        }
    if action is None:
        return {
            "kind": "help",
            "action": None,
            "card_type": card_type,
            "data": {
                "message": "hermes 处理课表、DDL、场地、活动、班车，以及按画像推荐公选/选修。",
                "capabilities": [
                    "课表",
                    "作业 DDL",
                    "研讨室",
                    "体育场馆",
                    "活动",
                    "班车",
                    "公选/画像匹配",
                ],
                "examples": [
                    "今天有什么课？",
                    "按我的画像推荐公选",
                    "南校园羽毛球还有吗？",
                ],
            },
            "requires_preview": False,
        }
    try:
        validated = CATALOG[action].params_type.model_validate(params)
    except ValidationError as exc:
        raw_issues = exc.errors(include_url=False)
        issues = [
            {
                "field": ".".join(str(part) for part in issue.get("loc", ())),
                "code": str(issue.get("type", "invalid")),
                "message": str(issue.get("msg", "参数无效")),
            }
            for issue in raw_issues
        ]
        required_fields = sorted(
            {
                str(issue["loc"][0])
                for issue in raw_issues
                if issue.get("type") == "missing" and issue.get("loc")
            }
        )
        form_screen = (
            "B6"
            if action.value.startswith("room.")
            else "B5"
            if action.value.startswith("gym.")
            else "B2"
        )
        return {
            "kind": "clarification",
            "action": action.value,
            "card_type": "parameter_clarification",
            "data": {
                "message": "需要补齐校园事务参数后才能继续。",
                "required_fields": required_fields,
                "provided_fields": sorted(params),
                "form_screen": form_screen,
                "issues": issues,
            },
            "requires_preview": False,
        }
    canonical_params = validated.model_dump(mode="json")
    if preview:
        return {
            "kind": "action_preview",
            "action": action.value,
            "card_type": card_type,
            "data": {"params": canonical_params, "next": "/actions/preview"},
            "requires_preview": True,
        }
    data = action_service.execute_read_action(db, user_id, action, canonical_params)
    return {
        "kind": "result",
        "action": action.value,
        "card_type": card_type,
        "data": data,
        "requires_preview": False,
    }
