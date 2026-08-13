"""Cast members reply in gathering chat when a real tester speaks.

This is not the proactive cast_driver tick. Production keeps
``ONEMORE_CAST_DRIVER_ENABLED=false``; these replies only fire after a
non-cast human sends a text message, at most one person, after a short delay.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.database import SessionLocal
from onemore.db.demo_cast import CAST_BY_ID, CAST_TASTE, CAST_USERS
from onemore.db.models import (
    Channel,
    ChannelParticipant,
    Gathering,
    Message,
    User,
)
from onemore.modules.cast_driver.catalog import CAST_USER_IDS, PERSONAS
from onemore.modules.collab import service as collab_service
from onemore.modules.taste_profile.llm_enrich import OPENCODE_GO_BASE_URL, OPENCODE_GO_MODEL, _api_key

logger = logging.getLogger("onemore.cast_driver.reactive_chat")

_CAST_IDS = frozenset(CAST_USER_IDS)
_pending_channels: set[str] = set()
_MAX_REPLY_CHARS = 36
_BANNED = ("作为ai", "作为 AI", "deepseek", "语言模型", "我是ai", "我是 AI")
_HOLLOW = {"嗯", "好", "行", "哦", "嗯嗯", "好的", "哦哦", "嗯好", "是", "对"}

_STYLE_HINT = {
    "talkative": "微信随手回，一两句，像同学帮忙。",
    "quiet": "话少，但要回正题。一句具体建议，不要只回嗯。",
    "balanced": "一句到两句，口语，有用。",
}


@dataclass(frozen=True)
class ReplyPlan:
    channel_id: str
    trigger_id: str
    sender_id: str
    responder_id: str
    delay_seconds: float


def reactive_chat_enabled() -> bool:
    settings = get_settings()
    if settings.env == "test":
        return False
    return bool(getattr(settings, "cast_reactive_chat_enabled", True))


def should_schedule(sender_id: str, content_type: str) -> bool:
    if not reactive_chat_enabled():
        return False
    if content_type != "text":
        return False
    return sender_id not in _CAST_IDS


def schedule_cast_replies(channel_id: str, message_id: str, sender_id: str) -> None:
    """Fire-and-forget from the API event loop. Dedupes in-flight channels."""

    if channel_id in _pending_channels:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _pending_channels.add(channel_id)
    task = loop.create_task(_run_cast_replies(channel_id, message_id, sender_id))
    task.add_done_callback(lambda _t: _pending_channels.discard(channel_id))


async def _run_cast_replies(channel_id: str, message_id: str, sender_id: str) -> None:
    try:
        plan = await asyncio.to_thread(build_plan, channel_id, message_id, sender_id)
        if plan is None:
            logger.info("cast chat skipped channel=%s", channel_id)
            return
        delay = asyncio.create_task(asyncio.sleep(plan.delay_seconds))
        text = await asyncio.to_thread(_compose_for_plan, plan)
        await delay
        message = await asyncio.to_thread(deliver_plan, plan, text)
        if message is None:
            return
        from onemore.modules.collab.realtime import hub
        from onemore.modules.collab.schemas import MessageView

        with SessionLocal() as db:
            allowed = collab_service.authorized_channel_user_ids(db, channel_id)
            payload = MessageView.model_validate(
                collab_service.message_view_data(message, db=db)
            ).model_dump(mode="json")
        await hub.broadcast(channel_id, payload, allowed_user_ids=allowed)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("cast reactive chat failed channel=%s", channel_id)


def build_plan(channel_id: str, trigger_id: str, sender_id: str) -> ReplyPlan | None:
    if sender_id in _CAST_IDS:
        return None
    with SessionLocal() as db:
        channel = db.get(Channel, channel_id)
        if channel is None or not channel.gathering_id:
            return None
        gathering = db.get(Gathering, channel.gathering_id)
        if gathering is None:
            return None
        member_ids = set(
            db.scalars(
                select(ChannelParticipant.user_id).where(
                    ChannelParticipant.channel_id == channel_id
                )
            )
        )
        cast_here = [user_id for user_id in CAST_USER_IDS if user_id in member_ids]
        if not cast_here:
            return None
        trigger = db.get(Message, trigger_id)
        if trigger is None or trigger.channel_id != channel_id:
            return None
        if trigger.sender_id in _CAST_IDS or trigger.content_type != "text":
            return None
        responder_id = _pick_responder(
            db, channel_id, cast_here, gathering.owner_user_id, trigger.content or ""
        )
        if responder_id is None:
            return None
        spec = CAST_BY_ID.get(responder_id)
        style = spec.interaction_style if spec else "balanced"
        delay = _delay_for(style)
        return ReplyPlan(
            channel_id=channel_id,
            trigger_id=trigger_id,
            sender_id=sender_id,
            responder_id=responder_id,
            delay_seconds=delay,
        )


def catch_up_if_needed(channel_id: str) -> None:
    """Re-schedule if a real user spoke and the in-memory task was lost."""

    if not reactive_chat_enabled():
        return
    with SessionLocal() as db:
        latest = _latest_real_text(db, channel_id)
        if latest is None or latest.sender_id in _CAST_IDS:
            return
        if _cast_already_replied_after(db, channel_id, latest.sent_at):
            return
        sent = latest.sent_at if latest.sent_at.tzinfo else latest.sent_at.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - sent).total_seconds()
        if age < 2 or age > 3600:
            return
        trigger_id, sender_id = latest.id, latest.sender_id
    schedule_cast_replies(channel_id, trigger_id, sender_id)


def _compose_for_plan(plan: ReplyPlan) -> str | None:
    with SessionLocal() as db:
        latest = _latest_real_text(db, plan.channel_id)
        if latest is None or latest.sender_id in _CAST_IDS:
            return None
        return compose_reply(db, plan.responder_id, plan.channel_id, latest)


def deliver_plan(plan: ReplyPlan, text: str | None = None) -> Message | None:
    with SessionLocal() as db:
        latest = _latest_real_text(db, plan.channel_id)
        if latest is None or latest.sender_id in _CAST_IDS:
            return None
        if _cast_already_replied_after(db, plan.channel_id, latest.sent_at):
            return None
        if not text:
            text = compose_reply(db, plan.responder_id, plan.channel_id, latest)
        if not text:
            return None
        return collab_service.send_message(db, plan.channel_id, plan.responder_id, text)


def compose_reply(db: Session, responder_id: str, channel_id: str, trigger: Message) -> str:
    incoming = trigger.content or ""
    fallback = _fallback_line(responder_id, incoming)
    try:
        generated = _llm_reply(db, responder_id, channel_id, trigger)
    except Exception:
        logger.info("cast chat llm fallback responder=%s", responder_id, exc_info=True)
        return fallback
    cleaned = _clean_reply(generated, fallback)
    if _is_canned_line(cleaned, responder_id) or _is_hollow(cleaned, incoming):
        return fallback
    return cleaned or fallback


def _pick_responder(
    db: Session,
    channel_id: str,
    cast_here: list[str],
    owner_id: str | None,
    trigger_text: str = "",
) -> str | None:
    recent = list(
        db.scalars(
            select(Message.sender_id)
            .where(
                Message.channel_id == channel_id,
                Message.sender_type == "human",
                Message.sender_id.in_(cast_here),
            )
            .order_by(Message.sent_at.desc())
            .limit(6)
        )
    )
    if recent and any(token in trigger_text for token in ("你觉得", "你用", "那你", "你呢", "你觉得")):
        last = recent[0]
        if last in cast_here:
            return last
    last_spoke = set(recent[:2])
    asked = _looks_like_question(trigger_text)
    weights: list[tuple[str, float]] = []
    for user_id in cast_here:
        spec = CAST_BY_ID.get(user_id)
        style = spec.interaction_style if spec else "balanced"
        weight = {"talkative": 3.0, "balanced": 1.6, "quiet": 0.55}.get(style, 1.0)
        if asked:
            weight = {"talkative": 4.0, "balanced": 2.2, "quiet": 0.25}.get(style, 1.0)
        if user_id == owner_id:
            weight += 0.8
        if user_id in last_spoke and not any(token in trigger_text for token in ("你觉得", "你用", "那你")):
            weight *= 0.35
        weights.append((user_id, weight))
    total = sum(item[1] for item in weights)
    if total <= 0:
        return cast_here[0]
    pick = random.random() * total
    upto = 0.0
    for user_id, weight in weights:
        upto += weight
        if pick <= upto:
            return user_id
    return weights[-1][0]


def _delay_for(style: str) -> float:
    if style == "quiet":
        return random.uniform(6.5, 11.0)
    if style == "talkative":
        return random.uniform(3.2, 6.5)
    return random.uniform(4.5, 8.5)


def _latest_real_text(db: Session, channel_id: str) -> Message | None:
    return db.scalar(
        select(Message)
        .where(
            Message.channel_id == channel_id,
            Message.sender_type == "human",
            Message.content_type == "text",
            Message.sender_id.notin_(tuple(_CAST_IDS)),
        )
        .order_by(Message.sent_at.desc())
        .limit(1)
    )


def _cast_already_replied_after(db: Session, channel_id: str, after: datetime) -> bool:
    sent_at = after if after.tzinfo else after.replace(tzinfo=UTC)
    existing = db.scalar(
        select(Message.id)
        .where(
            Message.channel_id == channel_id,
            Message.sender_id.in_(tuple(_CAST_IDS)),
            Message.sender_type == "human",
            Message.sent_at > sent_at - timedelta(milliseconds=50),
        )
        .limit(1)
    )
    return existing is not None


def _llm_reply(db: Session, responder_id: str, channel_id: str, trigger: Message) -> str:
    spec = CAST_BY_ID[responder_id]
    taste = CAST_TASTE.get(responder_id) or {}
    channel = db.get(Channel, channel_id)
    gathering = db.get(Gathering, channel.gathering_id) if channel and channel.gathering_id else None
    history = list(
        db.scalars(
            select(Message)
            .where(
                Message.channel_id == channel_id,
                Message.content_type == "text",
            )
            .order_by(Message.sent_at.desc())
            .limit(8)
        )
    )
    history.reverse()
    lines: list[str] = []
    for item in history:
        name = _speaker_label(db, item)
        text = (item.content or "").strip().replace("\n", " ")
        if not text:
            continue
        lines.append(f"{name}: {text[:80]}")
    transcript = "\n".join(lines[-8:])
    last = (trigger.content or "").strip().replace("\n", " ")[:80]
    style = _STYLE_HINT.get(spec.interaction_style, _STYLE_HINT["balanced"])
    system = (
        f"你在微信群里扮演中大学生「{spec.display_name}」。"
        f"{spec.college}，{spec.campus}。{style}\n"
        f"人设只用来定语气：{(taste.get('summary') or '')[:40]}\n"
        "只输出一条要发出去的正文。像同学在微信里随口帮一把：短、口语、有用。"
        "必须接对方最后一句。对方在问，就给一个具体建议，不要只回嗯、好、行。"
        "禁止小作文、禁止解释、禁止署名、禁止 emoji、禁止复述人设台词。"
        "一两句即可，不超过 28 个字。"
        "打招呼就回招呼；请客/带东西就接这个；问工具或入门就推荐一个好上手的。"
        "不要说赶图、耳机、下楼、海报。"
    )
    user = (
        f"局：{(gathering.title if gathering else '这局')}。\n"
        f"最近：\n{transcript}\n"
        f"对方刚说：「{last}」\n"
        "用一两句短消息接这句话，要有用。"
    )
    return _complete_plain_chat(system=system, user=user)


def _speaker_label(db: Session, message: Message) -> str:
    if message.sender_type == "azou":
        return "噜噜"
    if message.sender_type == "system":
        return "系统"
    if message.sender_id in CAST_BY_ID:
        return CAST_BY_ID[message.sender_id].display_name
    user = db.get(User, message.sender_id)
    return (user.display_name if user and user.display_name else "同学")


def _fallback_line(responder_id: str, incoming: str) -> str:
    spec = CAST_BY_ID.get(responder_id)
    quiet = bool(spec and spec.interaction_style == "quiet")
    text = incoming or ""
    if any(token in text for token in ("你好", "大家好", "哈喽", "在吗", "hi", "Hi", "hello")):
        if quiet:
            return "嗯好"
        if spec and spec.id == "u_demo_3":
            return "你好呀"
        if spec and spec.id == "u_demo_4":
            return "来了"
        return "你好"
    if any(token in text for token in ("奶茶", "咖啡", "带一点", "带杯", "喝的", "外卖")):
        if quiet:
            return "不用啦"
        if spec and spec.id == "u_demo_3":
            return "好啊谢谢"
        return "好啊"
    if any(token in text for token in ("入门", "好用", "哪个", "推荐", "比较", "工具", "编程", "vscode", "VS Code", "IDE", "用什么")):
        if quiet:
            return "Cursor，好上手"
        if spec and spec.id == "u_demo_1":
            return "刚入门用 Cursor 就行"
        return "Cursor 吧，好上手"
    if _looks_like_question(text):
        return "可以" if quiet else "好啊，我到时候说"
    return "收到" if quiet else "好"


def _looks_like_question(text: str) -> bool:
    return bool(
        "?" in text
        or "？" in text
        or any(token in text for token in ("吗", "嘛", "呢", "哪个", "什么", "怎么", "要不要", "能不能", "入门", "好用", "推荐"))
    )


def _is_hollow(text: str, incoming: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if compact not in _HOLLOW:
        return False
    return _looks_like_question(incoming) or len(re.sub(r"\s+", "", incoming)) >= 6


def _is_canned_line(text: str, responder_id: str) -> bool:
    persona = PERSONAS.get(responder_id)
    if not persona or not text:
        return False
    compact = re.sub(r"\s+", "", text)
    for line in persona.chat_lines:
        canned = re.sub(r"\s+", "", line)
        if compact == canned:
            return len(compact) >= 6
        if len(compact) >= 6 and (compact in canned or canned in compact):
            return True
    return False


def _clean_reply(text: str, fallback: str) -> str:
    cleaned = (text or "").strip().strip("「」\"'")
    cleaned = re.sub(r"\s+", "", cleaned)
    lowered = cleaned.lower()
    if any(token in lowered for token in _BANNED):
        return fallback
    for sep in ("。", "！", "？", "\n", "；"):
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[0]
            break
    if len(cleaned) > 22:
        for sep in ("，", ",", "、"):
            if sep in cleaned:
                head = cleaned.split(sep, 1)[0]
                if 2 <= len(head) <= 16:
                    cleaned = head
                    break
    if len(cleaned) > _MAX_REPLY_CHARS:
        cleaned = cleaned[:_MAX_REPLY_CHARS].rstrip("，,。！？； ")
    if len(cleaned) < 1:
        return fallback
    return cleaned


def _complete_plain_chat(*, system: str, user: str) -> str:
    settings = get_settings()
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("ONEMORE_TASTE_LLM_API_KEY is not configured")
    base_url = (getattr(settings, "taste_llm_base_url", None) or OPENCODE_GO_BASE_URL).rstrip("/")
    model = getattr(settings, "taste_llm_model", None) or OPENCODE_GO_MODEL
    body = {
        "model": model,
        "temperature": 0.55,
        "max_tokens": 64,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "ONE-MORE/1.0 (+https://github.com/onemore; cast-chat)",
        "Accept": "application/json",
    }
    url = f"{base_url}/chat/completions"
    with httpx.Client(timeout=18.0) as client:
        response = client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            raise RuntimeError(f"opencode go http {response.status_code}: {response.text[:300]}")
        payload = response.json()
    message = ((payload.get("choices") or [{}])[0]).get("message") or {}
    content = (message.get("content") or "").strip()
    if not content:
        raise RuntimeError("empty llm content")
    return content


# Imported by tests; keep CAST_USERS referenced so roster stays in sync.
assert {item.id for item in CAST_USERS} == set(CAST_USER_IDS)
