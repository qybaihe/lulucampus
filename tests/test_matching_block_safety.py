from __future__ import annotations

import pytest
from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import Gathering, GatheringMember


def _publish_same_three_person_intent(client, user_id: str) -> str:
    headers = {"X-User-ID": user_id}
    compiled = client.post(
        "/intent/compile",
        headers=headers,
        json={"text": "周六晚上珠海校区一起打羽毛球，3个人"},
    )
    assert compiled.status_code == 200, compiled.text
    card_id = compiled.json()["data"]["card"]["id"]
    published = client.post(
        "/intent/publish", headers=headers, json={"card_id": card_id}
    )
    assert published.status_code == 201, published.text
    return card_id


@pytest.mark.parametrize(
    ("blocker", "blocked"),
    [
        ("u_demo_1", "u_demo_3"),  # source/existing member ↔ candidate
        ("u_demo_2", "u_demo_3"),  # candidate ↔ candidate
    ],
)
def test_matching_never_forms_a_group_containing_any_blocked_pair(
    client, admin_headers, blocker, blocked
):
    card_ids = {
        _publish_same_three_person_intent(client, user_id)
        for user_id in ("u_demo_1", "u_demo_2", "u_demo_3")
    }
    assert (
        client.post(
            f"/me/blocks/{blocked}", headers={"X-User-ID": blocker}
        ).status_code
        == 201
    )
    run = client.post("/internal/matching/run", headers=admin_headers)
    assert run.status_code == 200, run.text

    with SessionLocal() as db:
        gathering_ids = list(
            db.scalars(
                select(Gathering.id).where(Gathering.source_intent_id.in_(card_ids))
            )
        )
        for gathering_id in gathering_ids:
            members = set(
                db.scalars(
                    select(GatheringMember.user_id).where(
                        GatheringMember.gathering_id == gathering_id,
                        GatheringMember.left_at.is_(None),
                    )
                )
            )
            assert not {blocker, blocked}.issubset(members)
