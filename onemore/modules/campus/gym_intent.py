"""Infer gym booking fields from Hermes natural-language questions."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
SPORTS = ("羽毛球", "健身", "游泳", "网球", "乒乓球", "篮球", "排球")
GYM_WORDS = ("场馆", "体育馆", *SPORTS)
BOOKING_MARKERS = ("预约", "预订", "订一个", "帮我订", "订场", "约一个", "约一场")
CAMPUSES = ("珠海校区", "南校园", "东校园", "北校园", "深圳校区")


def is_gym_booking_intent(text: str) -> bool:
    body = text or ""
    return any(marker in body for marker in BOOKING_MARKERS) and any(
        word in body for word in GYM_WORDS
    )


_GYM_BOOK_FIELDS = ("venue_type", "venue", "date", "start", "end")


def infer_gym_book_params(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = dict(context or {})
    params = {
        key: raw[key]
        for key in _GYM_BOOK_FIELDS
        if raw.get(key) not in (None, "", [])
    }
    body = text or ""
    if not params.get("venue_type"):
        for sport in SPORTS:
            if sport in body:
                params["venue_type"] = sport
                break
    today = datetime.now(SHANGHAI).date()
    if not params.get("date"):
        if "后天" in body:
            params["date"] = (today + timedelta(days=2)).isoformat()
        elif "明天" in body:
            params["date"] = (today + timedelta(days=1)).isoformat()
        else:
            params["date"] = today.isoformat()
    if not params.get("start"):
        params["start"] = "19:00"
        params["end"] = params.get("end") or "21:00"
    elif not params.get("end"):
        params["end"] = "21:00"
    if not params.get("venue"):
        for campus in CAMPUSES:
            if campus in body:
                params["venue"] = campus
                break
        if not params.get("venue") and raw.get("campus"):
            campus = str(raw.get("campus") or "").strip()
            if campus:
                params["venue"] = campus
    return params


def gym_preview_message(params: dict[str, Any]) -> str:
    sport = str(params.get("venue_type") or "场馆")
    venue = str(params.get("venue") or "").strip()
    day = str(params.get("date") or "")
    start = str(params.get("start") or "")
    end = str(params.get("end") or "")
    today = datetime.now(SHANGHAI).date().isoformat()
    when = "今晚" if day == today else day
    slot = f"{start}–{end}" if start and end else start
    place = f"{venue}{sport}" if venue else sport
    lead = " ".join(part for part in (when, slot, place) if part)
    return f"{lead}可以约。预览在下面，确认后才会真正下单。"
