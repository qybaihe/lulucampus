from __future__ import annotations


def _register(client, phone="13800001234", password="secret123", display_name=None):
    body = {"phone": phone, "password": password}
    if display_name is not None:
        body["display_name"] = display_name
    return client.post("/auth/register", json=body)


def test_register_returns_token_and_default_display_name(client):
    response = _register(client)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["access_token"].startswith("om1.")
    assert data["is_new_user"] is True
    assert data["display_name"] == "同学1234"

    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["data"]["user_id"] == data["user_id"]


def test_register_with_custom_display_name(client):
    response = _register(client, display_name="小白")
    assert response.status_code == 201
    assert response.json()["data"]["display_name"] == "小白"


def test_register_rejects_duplicate_phone(client):
    assert _register(client).status_code == 201
    duplicate = _register(client, password="another-pass")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PHONE_ALREADY_REGISTERED"


def test_register_rejects_invalid_phone_or_short_password(client):
    bad_phone = _register(client, phone="12345")
    assert bad_phone.status_code == 422
    short_password = _register(client, password="123")
    assert short_password.status_code == 422


def test_login_success_and_wrong_password(client):
    _register(client)

    ok = client.post(
        "/auth/login", json={"phone": "13800001234", "password": "secret123"}
    )
    assert ok.status_code == 200
    data = ok.json()["data"]
    assert data["access_token"].startswith("om1.")
    assert data["is_new_user"] is False

    wrong = client.post(
        "/auth/login", json={"phone": "13800001234", "password": "wrong-pass"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_phone_uses_same_error(client):
    response = client.post(
        "/auth/login", json={"phone": "13911112222", "password": "whatever1"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_registered_user_can_use_authenticated_apis(client):
    token = _register(client).json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    privacy = client.get("/me/privacy", headers=headers)
    assert privacy.status_code == 200

    trust = client.get("/trust/me", headers=headers)
    assert trust.status_code == 200
