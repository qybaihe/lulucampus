from __future__ import annotations


def _relation_channel(client) -> str:
    relations = client.get("/relations", headers={"X-User-ID": "u_demo_1"}).json()["data"]
    relation = next(
        item
        for item in relations
        if any(participant["user_id"] == "u_demo_2" for participant in item["participants"])
    )
    return relation["channel_id"]


def _unlock_organizer(client, admin_headers) -> None:
    response = client.post(
        "/internal/trust/u_demo_1/organizer-verification",
        headers=admin_headers,
        json={"verified": True},
    )
    assert response.status_code == 200


def _template_payload() -> dict:
    return {
        "title": "每周工作坊",
        "goal": "跨专业共创",
        "gathering_type": "workshop",
        "location": "创新空间",
        "campus": "珠海校区",
        "min_size": 3,
        "target_size": 12,
        "duration_minutes": 90,
        "required_roles": ["product"],
        "recurrence_rule": "FREQ=WEEKLY",
    }


def test_template_edit_copy_and_deactivate_contract(
    client, admin_headers, auth_headers
):
    _unlock_organizer(client, admin_headers)
    created = client.post("/organizer/templates", headers=auth_headers, json=_template_payload())
    assert created.status_code == 201
    template_id = created.json()["data"]["id"]

    edited = client.patch(
        f"/organizer/templates/{template_id}",
        headers=auth_headers,
        json={"title": "双周工作坊", "duration_minutes": 120},
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["title"] == "双周工作坊"

    copied = client.post(
        f"/organizer/templates/{template_id}/copy",
        headers=auth_headers,
        json={"title": "工作坊副本"},
    )
    assert copied.status_code == 201
    assert copied.json()["data"]["id"] != template_id

    removed = client.delete(f"/organizer/templates/{template_id}", headers=auth_headers)
    assert removed.status_code == 200
    assert removed.json()["data"]["active"] is False
    ids = {item["id"] for item in client.get("/organizer/templates", headers=auth_headers).json()["data"]}
    assert template_id not in ids
    assert copied.json()["data"]["id"] in ids
    assert (
        client.post(
            f"/organizer/templates/{template_id}/instantiate",
            headers=auth_headers,
            json={"start_at": "2026-09-06T10:00:00+08:00"},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/organizer/templates/{copied.json()['data']['id']}",
            headers={"X-User-ID": "u_demo_2"},
            json={"title": "越权修改"},
        ).status_code
        in {403, 404}
    )


def test_appeal_list_detail_resolution_and_ownership(client, admin_headers, auth_headers):
    created = client.post(
        "/trust/appeal",
        headers=auth_headers,
        json={"reason": "我的到场记录有误，请复核活动签到日志。"},
    )
    assert created.status_code == 201
    appeal_id = created.json()["data"]["id"]
    assert created.json()["data"]["reason"].startswith("我的到场")
    assert client.get("/trust/appeals", headers=auth_headers).json()["data"][0]["id"] == appeal_id
    assert (
        client.get(
            f"/trust/appeals/{appeal_id}", headers={"X-User-ID": "u_demo_2"}
        ).status_code
        == 404
    )

    resolved = client.post(
        f"/internal/trust/appeals/{appeal_id}/resolve",
        headers=admin_headers,
        json={"status": "approved", "result": "已核对签到日志，申诉成立并完成修正。"},
    )
    assert resolved.status_code == 200
    result = client.get(f"/trust/appeals/{appeal_id}", headers=auth_headers).json()["data"]
    assert result["status"] == "approved"
    assert result["result"].startswith("已核对")
    assert result["decided_at"].endswith("Z")
    assert (
        client.post(
            f"/internal/trust/appeals/{appeal_id}/resolve",
            headers=admin_headers,
            json={"status": "rejected", "result": "重复处理"},
        ).status_code
        == 409
    )


def test_cross_device_notification_preferences_keep_system_boundary(client, auth_headers):
    initial = client.get("/me/notification-preferences", headers=auth_headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["categories"]["chat_messages"] is True
    updated = client.patch(
        "/me/notification-preferences",
        headers=auth_headers,
        json={
            "overall_enabled": True,
            "calendar_sync_enabled": True,
            "categories": {
                "gathering_updates": True,
                "action_updates": True,
                "chat_messages": False,
                "trust_updates": True,
                "competition_deadlines": False,
            },
        },
    )
    assert updated.status_code == 200
    data = client.get("/me/notification-preferences", headers=auth_headers).json()["data"]
    assert data["calendar_sync_enabled"] is True
    assert data["categories"]["chat_messages"] is False
    assert data["system_settings_managed_locally"] == [
        "notification_authorization",
        "calendar_authorization",
        "focus_mode",
    ]
    partial = client.patch(
        "/me/notification-preferences",
        headers=auth_headers,
        json={"categories": {"trust_updates": False}},
    ).json()["data"]
    assert partial["categories"]["trust_updates"] is False
    assert partial["categories"]["chat_messages"] is False
    channel_id = _relation_channel(client)
    client.post(
        f"/channels/{channel_id}/messages",
        headers={"X-User-ID": "u_demo_2"},
        json={"content_type": "text", "content": "偏好投递测试"},
    )
    notifications = client.get("/notifications", headers=auth_headers).json()["data"]
    chat = next(item for item in notifications if item["type"] == "chat_message")
    assert chat["payload"]["push_delivery_suppressed"] is True


def test_image_upload_and_typed_image_location_messages(client):
    channel_id = _relation_channel(client)
    owner = {"X-User-ID": "u_demo_1"}
    png = b"\x89PNG\r\n\x1a\n" + b"local-fixture-pixels"
    uploaded = client.post(
        "/media/images",
        headers={
            **owner,
            "Content-Type": "image/png",
            "X-Filename": "campus.png",
            "X-Image-Width": "32",
            "X-Image-Height": "24",
        },
        content=png,
    )
    assert uploaded.status_code == 201, uploaded.text
    image = uploaded.json()["data"]

    posted = client.post(
        f"/channels/{channel_id}/messages",
        headers=owner,
        json={
            "content_type": "image",
            "image": {"media_id": image["media_id"], "caption": "集合点"},
        },
    )
    assert posted.status_code == 201, posted.text
    assert posted.json()["data"]["content"] is None
    assert posted.json()["data"]["image"]["caption"] == "集合点"
    assert client.get(image["url"], headers={"X-User-ID": "u_demo_2"}).content == png
    assert client.get(image["url"], headers={"X-User-ID": "u_demo_3"}).status_code == 403

    located = client.post(
        f"/channels/{channel_id}/messages",
        headers={"X-User-ID": "u_demo_2"},
        json={
            "content_type": "location",
            "location": {
                "latitude": 22.348,
                "longitude": 113.598,
                "label": "珠海校区图书馆",
                "address": "香洲区大学路2号",
            },
        },
    )
    assert located.status_code == 201
    assert located.json()["data"]["location"]["label"] == "珠海校区图书馆"
    invalid = client.post(
        f"/channels/{channel_id}/messages",
        headers=owner,
        json={"content_type": "image", "content": "not-an-image"},
    )
    assert invalid.status_code == 422
    binary_response = client.get("/openapi.json").json()["paths"]["/media/images/{asset_id}"]["get"]["responses"]["200"]
    assert set(binary_response["content"]) == {
        "image/jpeg",
        "image/png",
        "image/heic",
        "image/heif",
    }
    assert all(
        item["schema"] == {"type": "string", "format": "binary"}
        for item in binary_response["content"].values()
    )


def test_private_channel_media_access_ends_when_relation_is_dissolved(client):
    owner = {"X-User-ID": "u_demo_1"}
    peer = {"X-User-ID": "u_demo_2"}
    relation = next(
        item
        for item in client.get("/relations", headers=owner).json()["data"]
        if any(member["user_id"] == "u_demo_2" for member in item["participants"])
    )
    channel_id = relation["channel_id"]
    png = b"\x89PNG\r\n\x1a\n" + b"revocable-private-image"
    uploaded = client.post(
        "/media/images",
        headers={**owner, "Content-Type": "image/png", "X-Filename": "private.png"},
        content=png,
    )
    media = uploaded.json()["data"]
    posted = client.post(
        f"/channels/{channel_id}/messages",
        headers=owner,
        json={"content_type": "image", "image": {"media_id": media["media_id"]}},
    )
    assert posted.status_code == 201
    assert client.get(media["url"], headers=peer).status_code == 200

    dissolved = client.delete(f"/relations/{relation['id']}", headers=owner)
    assert dissolved.status_code == 200
    assert client.get(f"/channels/{channel_id}/messages", headers=peer).status_code == 409
    assert client.get(media["url"], headers=peer).status_code == 403


def test_block_revokes_bidirectional_text_image_location_read_media_and_push(client):
    owner = {"X-User-ID": "u_demo_1"}
    peer = {"X-User-ID": "u_demo_2"}
    channel_id = _relation_channel(client)
    png = b"\x89PNG\r\n\x1a\n" + b"block-policy-private-image"
    uploaded = client.post(
        "/media/images",
        headers={**owner, "Content-Type": "image/png", "X-Filename": "blocked.png"},
        content=png,
    )
    media = uploaded.json()["data"]
    shared = client.post(
        f"/channels/{channel_id}/messages",
        headers=owner,
        json={"content_type": "image", "image": {"media_id": media["media_id"]}},
    )
    assert shared.status_code == 201
    assert client.get(media["url"], headers=peer).status_code == 200

    before_notifications = len(
        client.get("/notifications", headers=owner).json()["data"]
    )
    assert client.post("/me/blocks/u_demo_2", headers=owner).status_code == 201

    for actor in (owner, peer):
        denied_read = client.get(f"/channels/{channel_id}/messages", headers=actor)
        assert denied_read.status_code == 403
        assert denied_read.json()["error"]["code"] == "FORBIDDEN"
        for body in (
            {"content_type": "text", "content": "拉黑后不应送达"},
            {
                "content_type": "location",
                "location": {"latitude": 22.3, "longitude": 113.5, "label": "集合点"},
            },
            {"content_type": "image", "image": {"media_id": media["media_id"]}},
        ):
            assert (
                client.post(
                    f"/channels/{channel_id}/messages", headers=actor, json=body
                ).status_code
                == 403
            )

    assert client.get(media["url"], headers=peer).status_code == 403
    assert len(client.get("/notifications", headers=owner).json()["data"]) == before_notifications


def test_signed_gap_share_resolve_join_and_privacy_boundary(client, auth_headers):
    compiled = client.post(
        "/intent/compile",
        headers=auth_headers,
        json={
            "text": "周六晚上珠海校区一起打羽毛球，四个人",
            "clarification_round": 0,
            "answers": {},
        },
    )
    assert compiled.status_code == 200
    card = compiled.json()["data"]["card"]
    published = client.post(
        "/intent/publish", headers=auth_headers, json={"card_id": card["id"]}
    )
    gathering_id = published.json()["data"]["gathering_id"]

    assert (
        client.post(
            f"/gatherings/{gathering_id}/share",
            headers={"X-User-ID": "u_demo_2"},
        ).status_code
        == 403
    )
    created = client.post(f"/gatherings/{gathering_id}/share", headers=auth_headers)
    assert created.status_code == 201
    share = created.json()["data"]
    assert share["deep_link"].startswith("onemore://g/v1.")
    assert share["universal_link"].startswith("https://onemore.example/g/v1.")
    assert share["joinable"] is True
    assert not ({"participants", "member_count", "owner_user_id", "display_name"} & set(share))

    public = client.get(f"/shares/g/{share['share_token']}")
    assert public.status_code == 200
    assert public.json()["data"] == share
    assert client.get(f"/shares/g/{share['share_token']}x").status_code == 404

    joined = client.post(
        f"/shares/g/{share['share_token']}/join",
        headers={"X-User-ID": "u_demo_2"},
    )
    assert joined.status_code == 200
    assert joined.json()["data"]["id"] == gathering_id
    assert joined.json()["data"]["status"] == "Pooling"
    assert joined.json()["data"]["participants"] is None
    # 招募期暴露池内纯计数：owner + joiner = 2
    assert joined.json()["data"]["member_count"] == 2
