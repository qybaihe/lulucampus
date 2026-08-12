from __future__ import annotations

from datetime import UTC, datetime

import pytest

from onemore.core.database import SessionLocal
from onemore.core.errors import ForbiddenError
from onemore.db.models import (
    ChannelStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    Message,
)
from onemore.modules.collab import service


def test_reopened_channel_preserves_original_history_but_hides_it_from_replacement():
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="项目",
            mode="similar",
            title="补位历史隔离",
            goal="保留原成员记录",
            status=GatheringStatus.CONFIRMED.value,
            min_size=3,
            target_size=3,
            required_trust_level="T1",
        )
        db.add(gathering)
        db.flush()
        rows: dict[str, GatheringMember] = {}
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            row = GatheringMember(
                gathering_id=gathering.id,
                user_id=user_id,
                joined_via="owner" if user_id == "u_demo_1" else "intent",
            )
            rows[user_id] = row
            db.add(row)
        db.flush()
        channel = service.open_gathering_channel(db, gathering.id)
        old = Message(
            channel_id=channel.id,
            sender_id="u_demo_1",
            content_type="text",
            content="补位前的原成员协作记录",
        )
        db.add(old)
        db.commit()
        old_id = old.id

        channel.status = ChannelStatus.CLOSED.value
        rows["u_demo_3"].left_at = datetime.now(UTC)
        db.add(
            GatheringMember(
                gathering_id=gathering.id,
                user_id="u_demo_4",
                joined_via="backfill_fast_lane",
            )
        )
        db.commit()

        reopened = service.open_gathering_channel(db, gathering.id)
        db.commit()
        assert db.get(Message, old_id) is not None
        assert old_id in {
            item.id for item in service.list_messages(db, reopened.id, "u_demo_1")
        }
        assert service.list_messages(db, reopened.id, "u_demo_4") == []
        with pytest.raises(ForbiddenError):
            service.list_messages(db, reopened.id, "u_demo_3")

        new = service.send_message(
            db, reopened.id, "u_demo_1", "补位后的新消息", "text"
        )
        assert [item.id for item in service.list_messages(db, reopened.id, "u_demo_4")] == [
            new.id
        ]
