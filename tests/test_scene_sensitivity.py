from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from starlette.websockets import WebSocketDisconnect

from onemore.core.database import SessionLocal
from onemore.db.models import (
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
)
from onemore.modules.collab import service as collab_service


def test_server_scene_classifier_covers_real_venue_label_variants():
    sensitive = (
        "南校园图书馆自习区",
        "南校园图书馆三楼自习区",
        "南校图书馆 A 区",
        "东校园健身房自由力量区",
    )
    assert all(
        collab_service.classify_scene_sensitivity(item) == "sensitive_muted_onsite"
        for item in sensitive
    )
    assert collab_service.classify_scene_sensitivity("南校园图书馆研讨室 15-401") == "social"
    assert collab_service.classify_scene_sensitivity("东校园羽毛球场") == "social"


def _sensitive_channel() -> tuple[str, str]:
    with SessionLocal() as db:
        gathering = Gathering(
            owner_user_id="u_demo_1",
            gathering_type="自习",
            mode="similar",
            title="敏感场景测试",
            goal="安静完成学习",
            status=GatheringStatus.ACTIVE.value,
            min_size=3,
            target_size=3,
            required_trust_level="T1",
            location="南校园图书馆自习区",
            start_at=datetime.now(UTC) - timedelta(minutes=30),
            end_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db.add(gathering)
        db.flush()
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
            db.add(
                GatheringMember(
                    gathering_id=gathering.id,
                    user_id=user_id,
                    confirmation_status=ConfirmationStatus.CONFIRMED.value,
                    confirmed_at=datetime.now(UTC),
                )
            )
        db.flush()
        channel = collab_service.open_gathering_channel(db, gathering.id)
        db.commit()
        return gathering.id, channel.id


def test_sensitive_onsite_policy_blocks_text_image_location_and_azou(client):
    _, channel_id = _sensitive_channel()
    owner = {"X-User-ID": "u_demo_1"}
    policy = client.get(f"/channels/{channel_id}/scene-policy", headers=owner)
    assert policy.status_code == 200
    assert policy.json()["data"] | {
        "mode": "sensitive_muted_onsite",
        "phase": "onsite_muted",
        "sending_enabled": False,
        "live_connection_enabled": False,
        "source": "server_scene_policy",
    } == policy.json()["data"]
    for payload in (
        {"content_type": "text", "content": "现场找人"},
        {
            "content_type": "location",
            "location": {"latitude": 23.1, "longitude": 113.3, "label": "我在这里"},
        },
    ):
        response = client.post(
            f"/channels/{channel_id}/messages", headers=owner, json=payload
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SCENE_MUTED_ONSITE"
    mention = client.post(
        f"/channels/{channel_id}/mention-azou",
        headers=owner,
        json={"text": "@阿凑 现场找人"},
    )
    assert mention.status_code == 409
    assert mention.json()["error"]["code"] == "SCENE_MUTED_ONSITE"


def test_sensitive_websocket_closes_onsite_and_restores_after_end(client):
    gathering_id, channel_id = _sensitive_channel()
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(
            f"/channels/{channel_id}", headers={"X-User-ID": "u_demo_1"}
        ),
    ):
        pass
    assert closed.value.code == 4403

    with SessionLocal() as db:
        gathering = db.get(Gathering, gathering_id)
        assert gathering is not None
        gathering.end_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    policy = client.get(
        f"/channels/{channel_id}/scene-policy", headers={"X-User-ID": "u_demo_1"}
    ).json()["data"]
    assert policy["phase"] == "post_event"
    assert policy["sending_enabled"] is True
    sent = client.post(
        f"/channels/{channel_id}/messages",
        headers={"X-User-ID": "u_demo_1"},
        json={"content_type": "text", "content": "结束后复盘"},
    )
    assert sent.status_code == 201
