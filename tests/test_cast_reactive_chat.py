from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.demo_cast import CHEN, LIN, ZHOU
from onemore.db.models import (
    Channel,
    ChannelParticipant,
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    Message,
    TrustProfile,
    User,
)
from onemore.modules.cast_driver import reactive_chat
from onemore.modules.cast_driver.catalog import CAST_USER_IDS
from onemore.modules.collab import service as collab_service


def _guest(db, suffix: str) -> User:
    user = User(
        id=f"u_chat_{suffix}",
        display_name="白鹤测试",
        verified_at=datetime.now(UTC),
        social_enabled=True,
    )
    db.add(user)
    db.flush()
    db.add(TrustProfile(user_id=user.id, level="T1"))
    db.flush()
    return user


def _open_channel(db) -> tuple[Gathering, Channel]:
    gathering = db.scalar(select(Gathering).where(Gathering.title == "英东周三羽毛球"))
    assert gathering is not None
    channel = db.scalar(select(Channel).where(Channel.gathering_id == gathering.id))
    assert channel is not None
    return gathering, channel


def _join(db, gathering: Gathering, channel: Channel, user: User) -> None:
    db.add(
        GatheringMember(
            gathering_id=gathering.id,
            user_id=user.id,
            confirmation_status=ConfirmationStatus.CONFIRMED.value,
            joined_via="matching",
            confirmed_at=datetime.now(UTC),
        )
    )
    db.add(ChannelParticipant(channel_id=channel.id, user_id=user.id))
    db.commit()


def test_test_env_does_not_auto_schedule():
    assert reactive_chat.should_schedule("u_guest", "text") is False
    assert reactive_chat.should_schedule(LIN, "text") is False


def test_cast_member_speaking_does_not_plan_a_reply():
    with SessionLocal() as db:
        gathering, channel = _open_channel(db)
        message = collab_service.send_message(db, channel.id, LIN, "大家好")
        channel_id, message_id = channel.id, message.id
    plan = reactive_chat.build_plan(channel_id, message_id, LIN)
    assert plan is None


def test_real_user_gets_one_in_character_cast_reply(monkeypatch):
    monkeypatch.setattr(
        reactive_chat,
        "_llm_reply",
        lambda db, responder_id, channel_id, trigger: "门口见",
    )
    with SessionLocal() as db:
        gathering, channel = _open_channel(db)
        guest = _guest(db, "real")
        _join(db, gathering, channel, guest)
        trigger = collab_service.send_message(db, channel.id, guest.id, "大家好呀")
        channel_id, trigger_id, guest_id = channel.id, trigger.id, guest.id

    plan = reactive_chat.build_plan(channel_id, trigger_id, guest_id)
    assert plan is not None
    assert plan.responder_id in CAST_USER_IDS
    assert plan.responder_id != guest_id
    assert plan.delay_seconds >= 3

    reply = reactive_chat.deliver_plan(plan)
    assert reply is not None
    assert reply.sender_id == plan.responder_id
    assert reply.content == "门口见"

    again = reactive_chat.deliver_plan(plan)
    assert again is None


def test_fallback_greeting_matches_persona_when_llm_off(monkeypatch):
    monkeypatch.setattr(
        reactive_chat,
        "_llm_reply",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("no llm")),
    )
    text = reactive_chat._fallback_line(CHEN, "大家好呀")
    assert text == "你好呀"

    with SessionLocal() as db:
        gathering, channel = _open_channel(db)
        guest = _guest(db, "fallback")
        _join(db, gathering, channel, guest)
        trigger = collab_service.send_message(db, channel.id, guest.id, "大家好")
        plan = reactive_chat.ReplyPlan(
            channel_id=channel.id,
            trigger_id=trigger.id,
            sender_id=guest.id,
            responder_id=CHEN,
            delay_seconds=0,
        )
        reply = reactive_chat.deliver_plan(plan)
    assert reply is not None
    assert reply.sender_id == CHEN
    assert len(reply.content) <= 36


def test_message_view_exposes_cast_display_name_after_confirm():
    with SessionLocal() as db:
        gathering, channel = _open_channel(db)
        message = collab_service.send_message(db, channel.id, LIN, "场订好了")
        view = collab_service.message_view_data(message, db=db)
    assert view["sender_display_name"] == "林予安"


def test_clean_reply_keeps_one_short_clause():
    long = "你好呀，到时候我们在南校园博物馆门口集合，我可以带路。"
    assert reactive_chat._clean_reply(long, "好") == "你好呀"
    assert len(reactive_chat._clean_reply("嗯好那就按成局卡时间见哦谢谢", "好")) <= 36


def test_fallback_answers_the_last_message_not_persona_script():
    assert "赶图" not in reactive_chat._fallback_line(CHEN, "有没有想喝奶茶的我可以带一点～")
    assert reactive_chat._fallback_line(CHEN, "有没有想喝奶茶的我可以带一点～") == "好啊谢谢"
    assert "Cursor" in reactive_chat._fallback_line(LIN, "你们大家都用什么编程工具呀")
    beginner = "你觉得哪个比较好用 我刚入门"
    assert reactive_chat._fallback_line(ZHOU, beginner) != "嗯"
    assert "Cursor" in reactive_chat._fallback_line(ZHOU, beginner)
    assert reactive_chat._is_hollow("嗯", beginner)
    assert reactive_chat._is_canned_line("我戴耳机赶图，结束一起下楼。", CHEN)


def test_compose_reply_drops_canned_persona_line(monkeypatch):
    monkeypatch.setattr(
        reactive_chat,
        "_llm_reply",
        lambda db, responder_id, channel_id, trigger: "我戴耳机赶图，结束一起下楼。",
    )
    with SessionLocal() as db:
        gathering, channel = _open_channel(db)
        guest = _guest(db, "tea")
        _join(db, gathering, channel, guest)
        trigger = collab_service.send_message(
            db, channel.id, guest.id, "有没有想喝奶茶的我可以带一点～"
        )
        text = reactive_chat.compose_reply(db, CHEN, channel.id, trigger)
    assert text == "好啊谢谢"
    assert "赶图" not in text
    assert "下楼" not in text


def test_compose_reply_rejects_hollow_hmm(monkeypatch):
    monkeypatch.setattr(
        reactive_chat,
        "_llm_reply",
        lambda db, responder_id, channel_id, trigger: "嗯",
    )
    with SessionLocal() as db:
        gathering, channel = _open_channel(db)
        guest = _guest(db, "beginner")
        _join(db, gathering, channel, guest)
        trigger = collab_service.send_message(
            db, channel.id, guest.id, "你觉得哪个比较好用 我刚入门"
        )
        text = reactive_chat.compose_reply(db, ZHOU, channel.id, trigger)
    assert text != "嗯"
    assert "Cursor" in text
