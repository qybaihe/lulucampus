"""全量 UI 截图取证的演示数据。

产出（JSON 到 stdout）：
- pooling_id     带一句话心情的匿名池局（3/4 人，可开缺口卡）
- tentative_id   u_demo_1 待确认的局（触发座满仪式/破冰包）
- confirmed_id   已成局 + 群聊（系统成局卡首条消息）
- channel_id     上述已成局的群聊
- completed_id   今天完成的局（复局三选一入口）
- relation_id    u_demo_1 的一段活跃搭子关系
- competition_id 一场比赛（赛事详情页）
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from onemore.core.database import SessionLocal
from onemore.db.models import (
    CompetitionEvent,
    Gathering,
    GatheringMember,
    GatheringStatus,
    IntentCard,
    IntentStatus,
    Relation,
)
from onemore.modules.collab.service import open_gathering_channel


def _gathering(
    db,
    *,
    owner: str,
    title: str,
    gathering_type: str,
    status: str,
    members: dict[str, str],
    start_offset: timedelta,
    duration: timedelta = timedelta(hours=2),
    location: str = "珠海校区综合馆",
    mood_intent_id: str | None = None,
    completed_at: datetime | None = None,
    target_size: int = 4,
    roles: dict[str, str] | None = None,
    # 演示用户的社交底线是「最少 3 人成局」，min_size 低于 3 会触发隐私拦截。
    min_size: int = 3,
) -> Gathering:
    now = datetime.now(UTC)
    gathering = Gathering(
        source_intent_id=mood_intent_id,
        owner_user_id=owner,
        gathering_type=gathering_type,
        mode="similar",
        title=title,
        goal=f"{gathering_type}，认真出席不咕",
        status=status,
        min_size=min_size,
        target_size=target_size,
        required_trust_level="T0",
        campus="珠海校区",
        identity_disclosure="after_confirmed",
        start_at=now + start_offset,
        end_at=now + start_offset + duration,
        location=location,
        expires_at=now + timedelta(days=2),
        completed_at=completed_at,
    )
    db.add(gathering)
    db.flush()
    for uid, confirmation in members.items():
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id=uid,
                role=(roles or {}).get(uid),
                confirmation_status=confirmation,
                confirmed_at=None if confirmation == "pending" else now,
                completion_confirmed=completed_at is not None,
            )
        )
    return gathering


def seed() -> dict:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        intent = IntentCard(
            user_id="u_demo_1",
            status=IntentStatus.POOLING.value,
            gathering_type="羽毛球",
            mode="similar",
            goal="打两小时羽毛球，认真出汗",
            mood_note="考完试想出出汗，来个不咕的",
            expires_at=now + timedelta(days=1),
        )
        db.add(intent)
        db.flush()

        pooling = _gathering(
            db,
            owner="u_demo_1",
            title="周六羽毛球局",
            gathering_type="羽毛球",
            status=GatheringStatus.POOLING.value,
            members={"u_demo_1": "confirmed", "u_demo_2": "confirmed", "u_demo_3": "confirmed"},
            start_offset=timedelta(days=2, hours=3),
            mood_intent_id=intent.id,
        )

        tentative = _gathering(
            db,
            owner="u_demo_2",
            title="周四晚自习冲 DDL",
            gathering_type="DDL冲刺",
            status=GatheringStatus.TENTATIVE.value,
            members={"u_demo_1": "pending", "u_demo_2": "confirmed", "u_demo_3": "confirmed"},
            start_offset=timedelta(days=1, hours=4),
            duration=timedelta(hours=3),
            location="珠海校区图书馆",
            target_size=3,
        )

        confirmed = _gathering(
            db,
            owner="u_demo_1",
            title="周五桌游拼车局",
            gathering_type="桌游",
            status=GatheringStatus.CONFIRMED.value,
            members={"u_demo_1": "confirmed", "u_demo_2": "confirmed", "u_demo_3": "confirmed"},
            start_offset=timedelta(days=3, hours=2),
            location="珠海校区学生活动中心",
            roles={"u_demo_1": "组织", "u_demo_2": "带桌游", "u_demo_3": "记分"},
        )
        channel = open_gathering_channel(db, confirmed.id)

        completed = _gathering(
            db,
            owner="u_demo_1",
            title="今晨操场夜跑局",
            gathering_type="夜跑",
            status=GatheringStatus.COMPLETED.value,
            members={"u_demo_1": "confirmed", "u_demo_2": "confirmed"},
            start_offset=timedelta(hours=-14),
            duration=timedelta(hours=1),
            location="珠海校区田径场",
            completed_at=now - timedelta(hours=12),
            target_size=2,
        )

        relation = (
            db.query(Relation)
            .filter(
                Relation.status == "active",
                (Relation.participant_a_id == "u_demo_1")
                | (Relation.participant_b_id == "u_demo_1"),
            )
            .first()
        )
        competition = db.query(CompetitionEvent).first()

        db.commit()
        return {
            "pooling_id": pooling.id,
            "tentative_id": tentative.id,
            "confirmed_id": confirmed.id,
            "channel_id": channel.id,
            "completed_id": completed.id,
            "relation_id": relation.id if relation else None,
            "competition_id": competition.id if competition else None,
        }


if __name__ == "__main__":
    print(json.dumps(seed(), ensure_ascii=False))
