"""联调演示数据：社交层截图取证用。

创建：
1. Pooling 局（带一句话心情，3/4 人，可生成缺口卡）
2. Tentative 局（其余成员已确认，u_demo_1 最后确认 → 触发座满仪式/破冰包/成局卡）
并输出既有 u_demo_1 关系 ID，供深链截图。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    IntentCard,
    IntentStatus,
    Relation,
)


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
        pooling = Gathering(
            source_intent_id=intent.id,
            owner_user_id="u_demo_1",
            gathering_type="羽毛球",
            mode="similar",
            title="周六羽毛球局",
            goal="打两小时羽毛球，认真出汗",
            status=GatheringStatus.POOLING.value,
            min_size=2,
            target_size=4,
            required_trust_level="T0",
            campus="珠海校区",
            identity_disclosure="after_confirmed",
            start_at=now + timedelta(days=2, hours=3),
            end_at=now + timedelta(days=2, hours=5),
            location="珠海校区综合馆",
            expires_at=now + timedelta(days=1),
        )
        db.add(pooling)
        db.flush()
        for uid in ["u_demo_1", "u_demo_2", "u_demo_3"]:
            db.add(
                GatheringMember(
                    gathering_id=pooling.id,
                    user_id=uid,
                    confirmation_status="confirmed",
                )
            )

        tentative = Gathering(
            owner_user_id="u_demo_2",
            gathering_type="DDL冲刺",
            mode="similar",
            title="周四晚自习冲 DDL",
            goal="图书馆三小时，各自赶作业互相看住",
            status=GatheringStatus.TENTATIVE.value,
            min_size=3,
            target_size=3,
            required_trust_level="T0",
            campus="珠海校区",
            identity_disclosure="after_confirmed",
            start_at=now + timedelta(days=1, hours=4),
            end_at=now + timedelta(days=1, hours=7),
            location="珠海校区图书馆",
            expires_at=now + timedelta(days=1),
        )
        db.add(tentative)
        db.flush()
        members = {
            "u_demo_1": "pending",
            "u_demo_2": "confirmed",
            "u_demo_3": "confirmed",
        }
        for uid, status in members.items():
            db.add(
                GatheringMember(
                    gathering_id=tentative.id,
                    user_id=uid,
                    confirmation_status=status,
                    confirmed_at=None if status == "pending" else now,
                )
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
        relation_id = relation.id if relation else None

        db.commit()
        return {
            "pooling_gathering_id": pooling.id,
            "tentative_gathering_id": tentative.id,
            "relation_id": relation_id,
        }


if __name__ == "__main__":
    print(json.dumps(seed(), ensure_ascii=False))
