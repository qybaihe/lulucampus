from __future__ import annotations

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    IntentCard,
    IntentStatus,
    Profile,
    TrustLevel,
    TrustProfile,
    User,
)


def _compile(client, user_id: str, text: str = "周六晚上珠海校区一起打羽毛球，3人"):
    response = client.post(
        "/intent/compile",
        headers={"X-User-ID": user_id},
        json={"text": text},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["card"]


def _publish(client, user_id: str, text: str = "周六晚上珠海校区一起打羽毛球，3人"):
    headers = {"X-User-ID": user_id}
    card = _compile(client, user_id, text)
    patched = client.patch(
        f"/intent/{card['id']}", headers=headers, json={"campus": "南校园"}
    )
    assert patched.status_code == 200, patched.text
    card = patched.json()["data"]
    response = client.post(
        "/intent/publish",
        headers=headers,
        json={"card_id": card["id"]},
    )
    return card, response


def test_privacy_values_are_readable_and_patch_returns_full_current_state(client):
    headers = {"X-User-ID": "u_demo_1"}
    changed = client.patch(
        "/me/privacy",
        headers=headers,
        json={
            "course_matching_enabled": False,
            "identity_disclosure": "after_full",
            "same_gender_only": True,
            "minimum_group_size": 5,
        },
    )
    assert changed.status_code == 200, changed.text
    expected = changed.json()["data"]
    assert expected == client.get("/me/privacy", headers=headers).json()["data"]
    identity = client.get("/auth/me", headers=headers).json()["data"]
    for key, value in expected.items():
        assert identity[key] == value


def test_course_matching_opt_out_removes_verified_prefill_but_keeps_self_report(client):
    with SessionLocal() as db:
        profile = db.get(Profile, "u_demo_1")
        assert profile is not None
        profile.verified_tags = ["backend"]
        profile.self_reported_tags = ["visual_design"]
        profile.capability_vector = {"backend": 1.0, "visual_design": 0.7}
        db.commit()
    headers = {"X-User-ID": "u_demo_1"}
    stale_card = _compile(client, "u_demo_1")
    assert any(
        item["source"] == "verified" for item in stale_card["capabilities"]
    )
    assert (
        client.patch(
            "/me/privacy",
            headers=headers,
            json={"course_matching_enabled": False},
        ).status_code
        == 200
    )
    card = _compile(client, "u_demo_1")
    assert card["capabilities"] == [
        {"key": "visual_design", "source": "self_reported"}
    ]
    refreshed_stale = client.get(
        f"/intent/{stale_card['id']}", headers=headers
    ).json()["data"]
    assert all(
        item["source"] != "verified" for item in refreshed_stale["capabilities"]
    )


def test_social_opt_out_withdraws_preconfirmation_state_and_matching_rechecks(client, admin_headers):
    card_ids: list[str] = []
    for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
        card, published = _publish(client, user_id)
        assert published.status_code == 201, published.text
        card_ids.append(card["id"])
    assert (
        client.patch(
            "/me/privacy",
            headers={"X-User-ID": "u_demo_3"},
            json={"social_enabled": False},
        ).status_code
        == 200
    )
    assert client.post("/internal/matching/run", headers=admin_headers).status_code == 200
    with SessionLocal() as db:
        assert all(
            card.status == IntentStatus.WITHDRAWN.value
            for card in db.scalars(
                select(IntentCard).where(
                    IntentCard.user_id == "u_demo_3",
                    IntentCard.id.in_(card_ids),
                )
            )
        )
        test_gathering_ids = set(
            db.scalars(
                select(Gathering.id).where(Gathering.source_intent_id.in_(card_ids))
            )
        )
        matched_with_opted_out_user = db.scalar(
            select(GatheringMember.id)
            .join(Gathering, Gathering.id == GatheringMember.gathering_id)
            .where(
                Gathering.id.in_(test_gathering_ids),
                Gathering.status == GatheringStatus.TENTATIVE.value,
                GatheringMember.user_id == "u_demo_3",
                GatheringMember.left_at.is_(None),
            )
        )
        assert matched_with_opted_out_user is None


def test_minimum_group_preference_controls_compile_edit_and_existing_pool(client):
    headers = {"X-User-ID": "u_demo_1"}
    _, published = _publish(client, "u_demo_1")
    assert published.status_code == 201
    old_gathering_id = published.json()["data"]["gathering_id"]
    assert (
        client.patch(
            "/me/privacy",
            headers=headers,
            json={"minimum_group_size": 5},
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert db.get(Gathering, old_gathering_id).status == GatheringStatus.DISSOLVED.value

    card = _compile(client, "u_demo_1", "周六一起打羽毛球，3人")
    assert card["min_size"] == 5
    assert card["target_size"] == 5
    lowered = client.patch(
        f"/intent/{card['id']}",
        headers=headers,
        json={"min_size": 3},
    )
    assert lowered.status_code == 422
    assert lowered.json()["error"]["code"] == "GROUP_SIZE_BELOW_PREFERENCE"


def test_t1_cannot_publish_six_or_more_person_gathering(client):
    with SessionLocal() as db:
        trust = db.get(TrustProfile, "u_demo_1")
        assert trust is not None
        trust.level = TrustLevel.T1.value
        db.commit()
    card = _compile(client, "u_demo_1", "周六晚上珠海校区一起自习，8人")
    assert card["target_size"] == 8
    response = client.post(
        "/intent/publish",
        headers={"X-User-ID": "u_demo_1"},
        json={"card_id": card["id"]},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TRUST_LEVEL_REQUIRED"


def test_cross_college_matching_requires_t2_for_every_member(client, admin_headers):
    user_ids = ("u_demo_1", "u_demo_2", "u_demo_3")
    with SessionLocal() as db:
        for index, user_id in enumerate(user_ids):
            user = db.get(User, user_id)
            trust = db.get(TrustProfile, user_id)
            assert user is not None and trust is not None
            user.college = f"学院-{index}"
            trust.level = TrustLevel.T1.value
        db.commit()
    card_ids = []
    for user_id in user_ids:
        card, published = _publish(client, user_id)
        assert published.status_code == 201, published.text
        card_ids.append(card["id"])
    first = client.post("/internal/matching/run", headers=admin_headers)
    assert first.status_code == 200
    assert first.json()["data"]["formed"] == 0

    with SessionLocal() as db:
        for user_id in user_ids:
            trust = db.get(TrustProfile, user_id)
            assert trust is not None
            trust.level = TrustLevel.T2.value
        db.commit()
    second = client.post("/internal/matching/run", headers=admin_headers)
    assert second.status_code == 200
    assert second.json()["data"]["formed"] >= 1


def test_same_gender_tightening_removes_mixed_tentative_member_and_confirm_rechecks(
    client, admin_headers
):
    with SessionLocal() as db:
        first = db.get(User, "u_demo_1")
        second = db.get(User, "u_demo_2")
        third = db.get(User, "u_demo_3")
        assert first is not None and second is not None and third is not None
        first.gender_code = "female"
        second.gender_code = "male"
        third.gender_code = "female"
        db.commit()

    card_ids: list[str] = []
    for user_id in ("u_demo_1", "u_demo_2", "u_demo_3"):
        card, published = _publish(client, user_id)
        assert published.status_code == 201, published.text
        card_ids.append(card["id"])
    matched = client.post("/internal/matching/run", headers=admin_headers)
    assert matched.status_code == 200, matched.text

    with SessionLocal() as db:
        gathering = db.scalar(
            select(Gathering).where(
                Gathering.source_intent_id.in_(card_ids),
                Gathering.status == GatheringStatus.TENTATIVE.value,
            )
        )
        assert gathering is not None
        gathering_id = gathering.id

    tightened = client.patch(
        "/me/privacy",
        headers={"X-User-ID": "u_demo_1"},
        json={"same_gender_only": True},
    )
    assert tightened.status_code == 200, tightened.text
    with SessionLocal() as db:
        departed = db.scalar(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.user_id == "u_demo_1",
            )
        )
        assert departed is None or departed.left_at is not None

        # Independently prove confirmation also fails closed if a stale mixed
        # tentative group reaches this boundary without the PATCH cleanup path.
        remaining = list(
            db.scalars(
                select(GatheringMember).where(
                    GatheringMember.gathering_id == gathering_id,
                    GatheringMember.left_at.is_(None),
                )
            )
        )
        assert remaining
        stale_gathering = db.get(Gathering, gathering_id)
        assert stale_gathering is not None
        stale_gathering.status = GatheringStatus.TENTATIVE.value
        stale_user = db.get(User, remaining[0].user_id)
        assert stale_user is not None
        stale_user.same_gender_only = True
        db.commit()
        stale_user_id = stale_user.id

    rejected = client.post(
        f"/gatherings/{gathering_id}/confirm",
        headers={"X-User-ID": stale_user_id},
        json={"confirmed": True},
    )
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"]["code"] == "GATHERING_PRIVACY_CHANGED"
