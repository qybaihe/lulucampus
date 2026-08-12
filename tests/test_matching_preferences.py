from __future__ import annotations


def test_matching_preferences_are_private_persisted_and_patchable(client, auth_headers):
    initial = client.get("/me/matching-preferences", headers=auth_headers)
    assert initial.status_code == 200
    assert initial.json()["data"] == {
        "interaction_style": "balanced",
        "sport_level": "casual",
        "study_intensity": "balanced",
    }

    updated = client.patch(
        "/me/matching-preferences",
        headers=auth_headers,
        json={"interaction_style": "quiet", "study_intensity": "focused"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"] == {
        "interaction_style": "quiet",
        "sport_level": "casual",
        "study_intensity": "focused",
    }
    persisted = client.get("/me/matching-preferences", headers=auth_headers)
    assert persisted.json()["data"] == updated.json()["data"]
    assert client.get("/auth/me", headers={"X-User-ID": "u_demo_2"}).json()["data"].get(
        "matching_preferences"
    ) is None


def test_matching_preferences_reject_unknown_enums(client, auth_headers):
    response = client.patch(
        "/me/matching-preferences",
        headers=auth_headers,
        json={"sport_level": "professional"},
    )
    assert response.status_code == 422


def test_intent_uses_private_matching_preference_as_default(client, auth_headers):
    client.patch(
        "/me/matching-preferences",
        headers=auth_headers,
        json={"study_intensity": "focused"},
    )
    compiled = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={
            "text": "明晚一起论文冲刺 3 人",
            "clarification_round": 2,
            "answers": {},
        },
    )
    assert compiled.status_code == 200
    card = compiled.json()["data"]["card"]
    assert card["intensity"] == "focused"
    assert card["field_sources"]["intensity"] == "matching_preference"
