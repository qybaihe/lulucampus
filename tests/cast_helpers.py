from __future__ import annotations


def publish_aligned_intent(client, user_id: str, text: str, *, campus: str = "南校园"):
    """Compile + publish with a shared campus so mixed-campus cast users can match."""

    headers = {"X-User-ID": user_id}
    compiled = client.post("/intent/compile", headers=headers, json={"text": text})
    assert compiled.status_code == 200, compiled.text
    card = compiled.json()["data"]["card"]
    patched = client.patch(
        f"/intent/{card['id']}", headers=headers, json={"campus": campus}
    )
    assert patched.status_code == 200, patched.text
    published = client.post(
        "/intent/publish", headers=headers, json={"card_id": card["id"]}
    )
    assert published.status_code == 201, published.text
    return headers, patched.json()["data"], published.json()["data"]
