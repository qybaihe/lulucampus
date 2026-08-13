from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from onemore.core.time import ensure_utc
from onemore.db.models import Course, Enrollment, TimeWindow, User, utcnow
from onemore.modules.schedule.schemas import IntersectionView

CAMPUS_TRAVEL_MINUTES = {
    ("南校园", "东校园"): 50,
    ("东校园", "南校园"): 50,
    ("广州校区", "珠海校区"): 180,
    ("珠海校区", "广州校区"): 180,
    ("深圳校区", "广州校区"): 150,
    ("广州校区", "深圳校区"): 150,
}


def is_reachable(campus_a: str | None, campus_b: str | None, gap_minutes: int) -> bool:
    if not campus_a or not campus_b or campus_a == campus_b:
        return True
    required = CAMPUS_TRAVEL_MINUTES.get((campus_a, campus_b), 120)
    return gap_minutes >= required


def get_free_windows(db: Session, user_id: str) -> list[TimeWindow]:
    return list(
        db.scalars(
            select(TimeWindow).where(TimeWindow.user_id == user_id).order_by(TimeWindow.start_at)
        )
    )


def intersect_windows(
    db: Session,
    user_ids: list[str],
    *,
    start_after: datetime | None = None,
    end_before: datetime | None = None,
    minimum_minutes: int = 60,
) -> list[IntersectionView]:
    unique_ids = list(dict.fromkeys(user_ids))
    windows_by_user: dict[str, list[TimeWindow]] = {}
    for user_id in unique_ids:
        query = select(TimeWindow).where(TimeWindow.user_id == user_id)
        if start_after:
            query = query.where(TimeWindow.end_at > start_after)
        if end_before:
            query = query.where(TimeWindow.start_at < end_before)
        windows_by_user[user_id] = list(db.scalars(query.order_by(TimeWindow.start_at)))
    if any(not windows for windows in windows_by_user.values()):
        return []

    intersections: list[tuple[datetime, datetime, list[TimeWindow]]] = [
        (window.start_at, window.end_at, [window]) for window in windows_by_user[unique_ids[0]]
    ]
    for user_id in unique_ids[1:]:
        next_intersections: list[tuple[datetime, datetime, list[TimeWindow]]] = []
        for left_start, left_end, used in intersections:
            for right in windows_by_user[user_id]:
                normalized_left_start = ensure_utc(left_start)
                normalized_left_end = ensure_utc(left_end)
                normalized_right_start = ensure_utc(right.start_at)
                normalized_right_end = ensure_utc(right.end_at)
                start = max(normalized_left_start, normalized_right_start)
                end = min(normalized_left_end, normalized_right_end)
                if end - start >= timedelta(minutes=minimum_minutes):
                    next_intersections.append((start, end, [*used, right]))
        intersections = next_intersections
        if not intersections:
            break

    results: list[IntersectionView] = []
    seen: set[tuple[datetime, datetime]] = set()
    for start, end, used in sorted(intersections, key=lambda item: (item[0], item[1])):
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        campuses = [window.campus for window in used]
        reachable = all(
            is_reachable(campuses[i], campuses[j], int((end - start).total_seconds() / 60))
            for i in range(len(campuses))
            for j in range(i + 1, len(campuses))
        )
        results.append(
            IntersectionView(
                start_at=start,
                end_at=end,
                feasible_count=len(unique_ids),
                stability=round(sum(window.stability for window in used) / len(used), 4),
                campus_reachable=reachable,
            )
        )
    return [item for item in results if item.campus_reachable]


def _is_displayable_code(value: str | None) -> bool:
    """True when a course/class code is human-readable (not jwxt hashes / long teaching ids)."""

    if not value or not str(value).strip():
        return False
    text = str(value).strip()
    if text.lower().startswith("jwxt:"):
        return False
    if text.isdigit() and len(text) >= 12:
        return False
    if len(text) >= 28 and all(ch.isalnum() or ch in ":-_" for ch in text):
        return False
    return True


def _time_label(start_at: datetime, end_at: datetime | None = None) -> str:
    shanghai = ZoneInfo("Asia/Shanghai")
    start_local = ensure_utc(start_at).astimezone(shanghai)
    if end_at is None:
        return start_local.strftime("%H:%M")
    end_local = ensure_utc(end_at).astimezone(shanghai)
    return f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')}"


def _entry_dict(
    *,
    course_id: str,
    course_code: str,
    course_name: str,
    class_code: str,
    start_at: datetime,
    end_at: datetime,
    location: str | None,
    changed: bool = False,
) -> dict:
    display_code = course_code if _is_displayable_code(course_code) else None
    display_class = class_code if _is_displayable_code(class_code) else None
    return {
        "course_id": course_id,
        # Keep stored identifiers for detail links / debugging; clients must use
        # display_* fields for presentation so jwxt hashes never surface in UI.
        "course_code": course_code,
        "course_name": course_name,
        "class_code": class_code,
        "start_at": start_at,
        "end_at": end_at,
        "location": location,
        "changed": changed,
        "title": course_name,
        "time_label": _time_label(start_at, end_at),
        "display_code": display_code,
        "display_class_code": display_class,
    }


def iter_current_meetings(db: Session, user_id: str | None = None):
    query = (
        select(Enrollment, Course)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Enrollment.status == "current")
    )
    if user_id is not None:
        query = query.where(Enrollment.user_id == user_id)
    rows = db.execute(query).all()
    for enrollment, course in rows:
        for meeting in enrollment.meeting_windows or []:
            if not isinstance(meeting, dict):
                continue
            start_raw = meeting.get("start_at")
            end_raw = meeting.get("end_at")
            if not isinstance(start_raw, str) or not isinstance(end_raw, str):
                continue
            try:
                start_at = ensure_utc(datetime.fromisoformat(start_raw.replace("Z", "+00:00")))
                end_at = ensure_utc(datetime.fromisoformat(end_raw.replace("Z", "+00:00")))
            except ValueError:
                continue
            yield enrollment, course, meeting, start_at, end_at


def _iter_meeting_entries(db: Session, user_id: str):
    yield from iter_current_meetings(db, user_id)


def timetable_entries(db: Session, user_id: str, week: int) -> list[dict]:
    output: list[dict] = []
    for enrollment, course, meeting, start_at, end_at in _iter_meeting_entries(db, user_id):
        meeting_week = meeting.get("week")
        if meeting_week is not None and int(meeting_week) != week:
            continue
        output.append(
            _entry_dict(
                course_id=course.id,
                course_code=course.code,
                course_name=course.name,
                class_code=enrollment.class_code,
                start_at=start_at,
                end_at=end_at,
                location=meeting.get("location"),
                changed=bool(meeting.get("changed", False)),
            )
        )
    return sorted(output, key=lambda item: item["start_at"])


def timetable_entries_for_day(
    db: Session, user_id: str, day: datetime | None = None
) -> list[dict]:
    """Return course occurrences that fall on the local calendar day (Asia/Shanghai)."""

    shanghai = ZoneInfo("Asia/Shanghai")
    local_now = (day or datetime.now(UTC)).astimezone(shanghai)
    day_start = datetime.combine(local_now.date(), time.min, shanghai).astimezone(UTC)
    day_end = day_start + timedelta(days=1)
    output: list[dict] = []
    for enrollment, course, meeting, start_at, end_at in _iter_meeting_entries(db, user_id):
        if start_at < day_start or start_at >= day_end:
            continue
        output.append(
            _entry_dict(
                course_id=course.id,
                course_code=course.code,
                course_name=course.name,
                class_code=enrollment.class_code,
                start_at=start_at,
                end_at=end_at,
                location=meeting.get("location"),
                changed=bool(meeting.get("changed", False)),
            )
        )
    return sorted(output, key=lambda item: item["start_at"])


def _first_string(source: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _parse_instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _course_code(occurrence: dict[str, Any], course_name: str) -> str:
    raw_value = occurrence.get("raw")
    raw = cast(dict[str, Any], raw_value) if isinstance(raw_value, dict) else {}
    explicit = _first_string(
        raw,
        "courseCode",
        "course_code",
        "courseNum",
        "courseNumber",
        "courseId",
    )
    if explicit:
        return explicit[:64]
    digest = hashlib.sha256(course_name.encode()).hexdigest()[:16]
    return f"jwxt:{digest}"


def _class_code(occurrence: dict[str, Any], course_code: str) -> str:
    raw_value = occurrence.get("raw")
    raw = cast(dict[str, Any], raw_value) if isinstance(raw_value, dict) else {}
    explicit = _first_string(
        raw,
        "teachingClassId",
        "teachingClassID",
        "teachingClassCode",
        "classCode",
        "class_code",
    )
    return (explicit or _first_string(occurrence, "sourceGroupKey") or course_code)[:64]


def _replace_enrollments(
    db: Session, user_id: str, payload: dict[str, Any]
) -> tuple[int, list[tuple[datetime, datetime]]]:
    occurrences = payload.get("occurrences", [])
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    busy: list[tuple[datetime, datetime]] = []
    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            continue
        name = _first_string(occurrence, "courseName", "title")
        start_at = _parse_instant(occurrence.get("startAt"))
        end_at = _parse_instant(occurrence.get("endAt"))
        if not name or start_at is None or end_at is None or end_at <= start_at:
            continue
        code = _course_code(occurrence, name)
        grouped[(code, _class_code(occurrence, code))].append(occurrence)
        busy.append((start_at, end_at))

    db.execute(delete(Enrollment).where(Enrollment.user_id == user_id))
    term = str(payload.get("schoolYear") or "current")[:32]
    for (code, class_code), items in grouped.items():
        course = db.scalar(select(Course).where(Course.code == code))
        if course is None:
            name = _first_string(items[0], "courseName", "title") or code
            course = Course(
                code=code,
                name=name[:128],
                domain="general",
                capability_tags=[],
                course_type="unknown",
            )
            db.add(course)
            db.flush()
        meetings = []
        for item in items:
            start_at = _parse_instant(item.get("startAt"))
            end_at = _parse_instant(item.get("endAt"))
            if start_at is None or end_at is None:
                continue
            meetings.append(
                {
                    "week": item.get("weekly"),
                    "start_at": start_at.isoformat(),
                    "end_at": end_at.isoformat(),
                    "location": _first_string(item, "location"),
                }
            )
        db.add(
            Enrollment(
                user_id=user_id,
                course_id=course.id,
                class_code=class_code,
                term=term,
                status="current",
                course_type=course.course_type,
                meeting_windows=meetings,
            )
        )
    return len(grouped), busy


def _build_free_windows(db: Session, user_id: str, busy: list[tuple[datetime, datetime]]) -> int:
    db.execute(delete(TimeWindow).where(TimeWindow.user_id == user_id))
    shanghai = ZoneInfo("Asia/Shanghai")
    now = datetime.now(UTC).astimezone(shanghai)
    user = db.get(User, user_id)
    generated = 0
    for offset in range(0, 15):
        day = (now + timedelta(days=offset)).date()
        day_start = datetime.combine(day, time(9 if day.weekday() >= 5 else 8), shanghai)
        day_end = datetime.combine(day, time(22), shanghai)
        if offset == 0:
            rounded_now = now.replace(second=0, microsecond=0) + timedelta(minutes=15)
            day_start = max(day_start, rounded_now)
        if day_start >= day_end:
            continue
        relevant = sorted(
            (
                (max(day_start, start.astimezone(shanghai)), min(day_end, end.astimezone(shanghai)))
                for start, end in busy
                if start.astimezone(shanghai).date() == day
            ),
            key=lambda item: item[0],
        )
        cursor = day_start
        for start, end in relevant:
            buffered_start = max(day_start, start - timedelta(minutes=20))
            buffered_end = min(day_end, end + timedelta(minutes=20))
            if buffered_start - cursor >= timedelta(minutes=60):
                db.add(
                    TimeWindow(
                        user_id=user_id,
                        start_at=cursor.astimezone(UTC),
                        end_at=buffered_start.astimezone(UTC),
                        campus=user.campus if user else None,
                        recurring=True,
                        stability=0.85,
                    )
                )
                generated += 1
            cursor = max(cursor, buffered_end)
        if day_end - cursor >= timedelta(minutes=60):
            db.add(
                TimeWindow(
                    user_id=user_id,
                    start_at=cursor.astimezone(UTC),
                    end_at=day_end.astimezone(UTC),
                    campus=user.campus if user else None,
                    recurring=True,
                    stability=0.85,
                )
            )
            generated += 1
    return generated


def _schedule_signature(db: Session, user_id: str) -> str:
    rows = db.execute(
        select(Enrollment.class_code, Enrollment.term, Enrollment.meeting_windows).where(
            Enrollment.user_id == user_id
        )
    ).all()
    records = [(class_code, term, meetings) for class_code, term, meetings in rows]
    encoded = json.dumps(
        sorted(records, key=lambda item: (item[0], item[1], json.dumps(item[2], sort_keys=True))),
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def etl_term_timetable(db: Session, user_id: str, payload: dict | None = None) -> dict:
    """Normalize import-ready JWXT occurrences into enrollments and free-time indexes."""

    before = _schedule_signature(db, user_id)
    enrollment_count, busy = _replace_enrollments(db, user_id, payload or {"occurrences": []})
    generated = _build_free_windows(db, user_id, busy)
    db.commit()
    after = _schedule_signature(db, user_id)
    return {
        "enrollments_imported": enrollment_count,
        "windows_generated": generated,
        "changed": before != after,
        "updated_at": utcnow(),
    }


def weekly_delta_check(db: Session, user_id: str, payload: dict | None = None) -> dict:
    result = etl_term_timetable(db, user_id, payload)
    return {
        "user_id": user_id,
        "changes": ["timetable"] if result["changed"] else [],
        "checked_at": utcnow(),
        **result,
    }
