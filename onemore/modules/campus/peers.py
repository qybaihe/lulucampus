"""Opt-in social hints for Hermes: same course, same gym slot, or similar taste.

Only users with social_enabled are visible. NetID is never returned. One-tap
chat opens a 2-person confirmed gathering channel (Hermes spark).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.contact_policy import users_have_block_between
from onemore.core.errors import AppError, ForbiddenError, NotFoundError
from onemore.db.models import (
    CampusAction,
    ConfirmationStatus,
    Course,
    Enrollment,
    Gathering,
    GatheringMember,
    GatheringStatus,
    User,
    utcnow,
)
from onemore.modules.collab import service as collab_service
from onemore.modules.matching.service import _taste_similarity
from onemore.modules.taste_profile.service import public_interest_tags, taste_feature_set

MAX_PEERS = 6
SPORTS = ("羽毛球", "健身", "游泳", "网球", "乒乓球", "篮球", "排球")
SOCIAL_QUERY_MARKERS = (
    "还有谁",
    "同课",
    "一起上",
    "选了",
    "同学",
    "约了",
    "预约了",
    "同一时段",
    "感兴趣的人",
    "搭子",
    "一起去",
)
SOCIAL_CARDS = {
    "elective_match",
    "course_list",
    "gym_slots",
    "peer_list",
}
OVERLAPS = {"course", "gym", "taste"}


def context_from_ask_result(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    codes: list[str] = []
    for key in ("items", "courses"):
        rows = data.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = row.get("code") or row.get("course_code")
            if code:
                codes.append(str(code))
    params = data.get("params") if isinstance(data.get("params"), dict) else {}
    slots = data.get("slots") if isinstance(data.get("slots"), list) else []
    first_slot = slots[0] if slots and isinstance(slots[0], dict) else {}
    return {
        "course_codes": codes,
        "venue_type": params.get("venue_type") or data.get("venue_type") or first_slot.get("venue_type"),
        "date": params.get("date") or data.get("date"),
        "start": params.get("start") or data.get("start") or first_slot.get("start"),
        "venue": params.get("venue") or data.get("venue") or first_slot.get("venue"),
        "card_type": result.get("card_type"),
        "action": result.get("action"),
    }


def looks_like_social_query(text: str) -> bool:
    return any(marker in (text or "") for marker in SOCIAL_QUERY_MARKERS)


def should_attach_peers(result: dict[str, Any], question: str = "") -> bool:
    card = str(result.get("card_type") or "")
    if card in SOCIAL_CARDS:
        return True
    action = str(result.get("action") or "")
    if card == "action_preview" and action.startswith("gym."):
        return True
    return looks_like_social_query(question)


def suggest_peers(
    db: Session, user_id: str, context: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    me = db.get(User, user_id)
    if me is None or not me.social_enabled:
        return []
    context = _enrich_context(db, me, context or {})
    ranked: dict[str, dict[str, Any]] = {}

    def consider(peer_id: str, overlap: str, reason: str, score: float) -> None:
        if peer_id == user_id:
            return
        existing = ranked.get(peer_id)
        if existing is not None and score <= float(existing["_score"]):
            return
        peer = db.get(User, peer_id)
        if (
            peer is None
            or not peer.social_enabled
            or peer.account_status != "active"
            or users_have_block_between(db, user_id, peer_id)
        ):
            return
        if overlap == "course" and (not me.course_matching_enabled or not peer.course_matching_enabled):
            return
        if _gender_blocked(me, peer):
            return
        tags = public_interest_tags(db, peer_id, limit=2)
        ranked[peer_id] = {
            "user_id": peer_id,
            "display_name": (peer.display_name or "").strip() or "同学",
            "persona_label": tags[0] if tags else None,
            "reason": reason,
            "overlap": overlap,
            "_score": score,
        }

    codes = [str(code).strip() for code in (context.get("course_codes") or []) if str(code).strip()]
    if codes and me.course_matching_enabled:
        course_ids = list(db.scalars(select(Course.id).where(Course.code.in_(codes))))
        if course_ids:
            rows = db.execute(
                select(Enrollment.user_id, Course.code, Course.name)
                .join(Course, Course.id == Enrollment.course_id)
                .where(
                    Enrollment.course_id.in_(course_ids),
                    Enrollment.user_id != user_id,
                    Enrollment.status == "current",
                )
            ).all()
            for peer_id, code, name in rows:
                consider(str(peer_id), "course", f"也选了 {name}（{code}）", 3.0)

    venue_type = str(context.get("venue_type") or "").strip()
    day = str(context.get("date") or "").strip()
    start = str(context.get("start") or "").strip()
    if venue_type:
        cutoff = datetime.now(UTC) - timedelta(days=14)
        actions = db.scalars(
            select(CampusAction).where(
                CampusAction.user_id != user_id,
                CampusAction.action_name.in_(("gym.book_preview", "gym.book_commit")),
                CampusAction.created_at >= cutoff,
            )
        )
        for action in actions:
            params = action.params if isinstance(action.params, dict) else {}
            if str(params.get("venue_type") or "") != venue_type:
                continue
            if day and str(params.get("date") or "") != day:
                continue
            if start and str(params.get("start") or "") != start:
                continue
            consider(
                action.user_id,
                "gym",
                f"同一时段也想去{venue_type}",
                3.2,
            )

    if len(ranked) < MAX_PEERS:
        mine = taste_feature_set(db, user_id)
        if mine:
            candidates = list(
                db.scalars(
                    select(User.id).where(
                        User.id != user_id,
                        User.social_enabled.is_(True),
                        User.account_status == "active",
                    )
                )
            )
            scored: list[tuple[float, str]] = []
            for peer_id in candidates:
                if peer_id in ranked:
                    continue
                if not taste_feature_set(db, peer_id):
                    continue
                score = _taste_similarity(db, user_id, peer_id)
                if score >= 0.35:
                    scored.append((score, peer_id))
            scored.sort(reverse=True)
            for score, peer_id in scored[:MAX_PEERS]:
                tags = public_interest_tags(db, peer_id, limit=2)
                label = "、".join(tags[:2]) if tags else "兴趣相近"
                consider(peer_id, "taste", f"兴趣相近：{label}", 1.0 + score)

    ordered = sorted(ranked.values(), key=lambda item: -float(item["_score"]))[:MAX_PEERS]
    for item in ordered:
        item.pop("_score", None)
    return ordered


def start_peer_chat(
    db: Session,
    user: User,
    peer_user_id: str,
    *,
    reason: str = "",
    overlap: str = "taste",
) -> dict[str, str]:
    if not user.social_enabled:
        raise ForbiddenError("请先开启社交开关")
    if peer_user_id == user.id:
        raise AppError("PEER_INVALID", "不能和自己发起聊天", 400)
    peer = db.get(User, peer_user_id)
    if peer is None or not peer.social_enabled or peer.account_status != "active":
        raise NotFoundError("同学", peer_user_id)
    if users_have_block_between(db, user.id, peer_user_id):
        raise ForbiddenError("当前无法发起聊天")
    if overlap not in OVERLAPS:
        overlap = "taste"

    existing = _existing_spark(db, user.id, peer_user_id)
    if existing is not None:
        channel = collab_service.open_gathering_channel(db, existing.id)
        db.commit()
        return {"channel_id": channel.id, "gathering_id": existing.id}

    title = {
        "course": "一起上课",
        "gym": "一起去场馆",
    }.get(overlap, "Hermes 认识一下")
    gathering = Gathering(
        owner_user_id=user.id,
        gathering_type="sport" if overlap == "gym" else "study",
        mode="similar",
        title=title,
        goal=(reason or "Hermes 发现你们可能合得来").strip()[:500],
        status=GatheringStatus.CONFIRMED.value,
        min_size=2,
        target_size=2,
        identity_disclosure="after_confirmed",
        match_reason=reason or None,
        official_metadata={"created_via": "hermes_spark", "overlap": overlap},
        confirmation_deadline=datetime.now(UTC) + timedelta(days=3),
    )
    db.add(gathering)
    db.flush()
    now = utcnow()
    for member_id, via in ((user.id, "hermes"), (peer_user_id, "hermes_peer")):
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id=member_id,
                confirmation_status=ConfirmationStatus.CONFIRMED.value,
                joined_via=via,
                confirmed_at=now,
            )
        )
    db.flush()
    channel = collab_service.open_gathering_channel(db, gathering.id)
    db.commit()
    return {"channel_id": channel.id, "gathering_id": gathering.id}


def attach_peers(
    db: Session, user_id: str, result: dict[str, Any], *, question: str = ""
) -> dict[str, Any]:
    data = result.get("data")
    if not isinstance(data, dict):
        return result
    existing = data.get("peers")
    if isinstance(existing, list) and existing:
        return _with_peer_blurb(result, existing)
    if not should_attach_peers(result, question):
        return result
    context = context_from_ask_result(result)
    if question:
        context["question"] = question
    peers = suggest_peers(db, user_id, context)
    if not peers:
        return result
    updated = {**result, "data": {**data, "peers": peers}}
    return _with_peer_blurb(updated, peers)


def _with_peer_blurb(result: dict[str, Any], peers: list[dict[str, Any]]) -> dict[str, Any]:
    data = result.get("data")
    if not isinstance(data, dict) or not peers:
        return result
    message = str(data.get("message") or "")
    names = [str(item.get("display_name") or "") for item in peers if item.get("display_name")]
    if names and any(name and name in message for name in names):
        return result
    bits = [f"{item['display_name']}（{item['reason']}）" for item in peers[:3] if item.get("display_name")]
    if not bits:
        return result
    blurb = "可能合得来的人：" + "、".join(bits) + "。可以一键发起聊天。"
    merged = (message.rstrip() + "\n\n" + blurb) if message.strip() else blurb
    return {**result, "data": {**data, "message": merged}}


def _gender_blocked(me: User, peer: User) -> bool:
    if not me.same_gender_only and not peer.same_gender_only:
        return False
    if not me.gender_code or not peer.gender_code:
        return False
    return me.gender_code != peer.gender_code


def _enrich_context(db: Session, me: User, context: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(context)
    codes = [str(code).strip() for code in (enriched.get("course_codes") or []) if str(code).strip()]
    single = str(enriched.get("course_code") or "").strip()
    if single:
        codes.append(single)
    question = str(enriched.get("question") or "").strip()
    if question:
        lowered = question.lower()
        for course in db.scalars(select(Course)):
            if course.code.lower() in lowered or (len(course.name) >= 2 and course.name in question):
                codes.append(course.code)
        if not enriched.get("venue_type"):
            for sport in SPORTS:
                if sport in question:
                    enriched["venue_type"] = sport
                    break
    venue_type = str(enriched.get("venue_type") or "").strip()
    if venue_type:
        for course in db.scalars(select(Course)):
            if venue_type in (course.name or ""):
                codes.append(course.code)
    if (
        not codes
        and not venue_type
        and me.course_matching_enabled
        and looks_like_social_query(question)
    ):
        own = db.execute(
            select(Course.code)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.user_id == me.id, Enrollment.status == "current")
        ).all()
        codes.extend(str(code) for (code,) in own)
    # Preserve order, drop dupes.
    seen: list[str] = []
    for code in codes:
        if code not in seen:
            seen.append(code)
    enriched["course_codes"] = seen
    return enriched


def _existing_spark(db: Session, user_a: str, user_b: str) -> Gathering | None:
    cutoff = datetime.now(UTC) - timedelta(days=2)
    owned = list(
        db.scalars(
            select(Gathering).where(
                Gathering.owner_user_id.in_([user_a, user_b]),
                Gathering.status.in_(
                    {
                        GatheringStatus.CONFIRMED.value,
                        GatheringStatus.PREVIEWED.value,
                        GatheringStatus.ACTIVE.value,
                    }
                ),
                Gathering.created_at >= cutoff,
            )
        )
    )
    pair = {user_a, user_b}
    for gathering in owned:
        meta = gathering.official_metadata if isinstance(gathering.official_metadata, dict) else {}
        if meta.get("created_via") != "hermes_spark":
            continue
        members = set(
            db.scalars(
                select(GatheringMember.user_id).where(
                    GatheringMember.gathering_id == gathering.id,
                    GatheringMember.left_at.is_(None),
                )
            )
        )
        if members == pair:
            return gathering
    return None
