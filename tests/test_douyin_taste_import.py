from __future__ import annotations

import json
import time

from sqlalchemy import select

from onemore.core.database import SessionLocal
from onemore.db.models import TasteImportSession, TasteProfile
from onemore.modules.taste_profile import analyzer
from onemore.modules.taste_profile.providers import fake as fake_provider
from onemore.modules.taste_profile.service import items_path, runtime_dir_for

COOKIE_FLAGS = {"sessionid", "sessionid_ss", "sid_tt", "sid_guard"}
TERMINAL_WAIT = {"READY", "FAILED", "CANCELLED", "NEEDS_CONFIRMATION"}


def _wait_status(client, headers, import_id, statuses, timeout=8.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        response = client.get(f"/profile/imports/{import_id}", headers=headers).json()["data"]
        last = response
        if response["status"] in statuses:
            return response
        time.sleep(0.05)
    raise AssertionError(f"status never reached {statuses}; last={last and last['status']}")


def _create_import(client, headers, **payload):
    response = client.post("/profile/imports/douyin", headers=headers, json=payload)
    assert response.status_code == 202
    data = response.json()["data"]
    return response.json()["meta"], data


def _wait_qr(client, headers, import_id):
    return _wait_status(client, headers, import_id, {"WAITING_SCAN"})


def _wait_qr_version(client, headers, import_id, version, timeout=8.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = client.get(f"/profile/imports/{import_id}", headers=headers).json()["data"]
        if last["status"] == "WAITING_SCAN" and last["qr_version"] >= version:
            return last
        time.sleep(0.05)
    raise AssertionError(f"QR version never reached {version}; last={last}")


def _complete(client, headers, import_id):
    data = _wait_status(client, headers, import_id, TERMINAL_WAIT)
    # Analysis writes TasteProfile immediately; quiz is optional refinement.
    assert data["status"] == "READY"
    assert data["result"] is not None
    assert data["result"]["primary_tag"]["key"]
    assert data["result"].get("calibrated") is False
    return data


def _questions(client, headers, import_id):
    response = client.get(f"/profile/imports/{import_id}/questions", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]


def _answer_payload(questions):
    return {
        "answers": [
            {"question_id": q["id"], "option_id": q["options"][0]["id"]}
            for q in questions["questions"]
        ]
    }


def _dump_all_items(client, headers, import_id):
    items = []
    cursor = 0
    while True:
        page = client.get(
            f"/profile/imports/{import_id}/items?cursor={cursor}&limit=100", headers=headers
        ).json()["data"]
        items.extend(page["items"])
        if not page["has_more"]:
            return items
        cursor = page["next_cursor"]


# --------------------------------------------------------------------------- #
# creation / state machine
# --------------------------------------------------------------------------- #
def test_create_returns_immediately_and_polls(client, auth_headers):
    meta, data = _create_import(client, auth_headers)
    assert data["status"] == "PREPARING_QR"
    assert data["source"] == "douyin"
    assert data["result"] is None
    assert data["error"] is None
    assert meta["poll"] == f"/profile/imports/{data['id']}"
    assert meta["poll_after_seconds"] == 2


def test_fake_full_state_machine_stable_qr(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    waiting = _wait_qr(client, auth_headers, data["id"])
    assert waiting["qr_version"] == 0
    assert waiting["qr_image_data_url"].startswith("data:image")
    second = _wait_qr(client, auth_headers, data["id"])
    assert second["qr_image_data_url"] == waiting["qr_image_data_url"]

    done = _complete(client, auth_headers, data["id"])
    assert done["source_profile"]["sec_uid"].startswith("MS4wLjAB")
    assert done["collection"]["api_pages"] == 3
    assert done["collection"]["items_collected"] == 260
    assert done["collection"]["has_more"] is False
    assert done["question_count"] in range(3, 6)
    assert done["candidate_tags"]


def test_separate_qr_and_mobile_verification_apis(client, auth_headers, monkeypatch):
    monkeypatch.setattr(fake_provider, "_SCAN_DELAY_SECONDS", 60)
    created = client.post(
        "/profile/imports/douyin/qr?wait_seconds=2",
        headers=auth_headers,
        json={},
    )
    assert created.status_code == 202
    qr = created.json()["data"]
    assert qr["status"] == "WAITING_SCAN"
    assert qr["qr_image_data_url"].startswith("data:image")
    assert qr["qr_image_url"] == f"/profile/imports/{qr['import_id']}/qr/image?v=0"
    assert qr["verify"] == f"/profile/imports/{qr['import_id']}/verify"

    pending = client.post(
        f"/profile/imports/{qr['import_id']}/verify", headers=auth_headers
    )
    assert pending.status_code == 200
    assert pending.json()["data"]["verified"] is False
    assert pending.json()["data"]["status"] == "WAITING_SCAN"

    qr_only = client.get(
        f"/profile/imports/{qr['import_id']}/qr", headers=auth_headers
    )
    assert qr_only.status_code == 200
    assert qr_only.json()["data"]["qr_image_data_url"] == qr["qr_image_data_url"]
    image = client.get(qr["qr_image_url"], headers=auth_headers)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.headers["cache-control"].startswith("no-store")
    assert image.content.startswith(b"\x89PNG")

    monkeypatch.setattr(fake_provider, "_SCAN_DELAY_SECONDS", 0.15)
    verified = client.post(
        f"/profile/imports/{qr['import_id']}/verify?wait_seconds=3",
        headers=auth_headers,
    )
    assert verified.status_code == 200
    assert verified.json()["data"]["verified"] is True
    _complete(client, auth_headers, qr["import_id"])


def test_qr_then_phone_verification_path_keeps_secrets_private(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(fake_provider, "_PHONE_REQUIRED", True)
    monkeypatch.setattr(fake_provider, "_SCAN_DELAY_SECONDS", 60)
    _, created = _create_import(client, auth_headers)
    waiting = _wait_qr(client, auth_headers, created["id"])

    before_scan = client.post(
        f"/profile/imports/{waiting['id']}/phone/code",
        headers=auth_headers,
        json={"phone": "13800138000", "country_code": "86"},
    )
    assert before_scan.status_code == 409
    assert before_scan.json()["error"]["code"] == "DOUYIN_SCAN_REQUIRED"

    monkeypatch.setattr(fake_provider, "_SCAN_DELAY_SECONDS", 0.15)
    phone_required = _wait_status(
        client, auth_headers, waiting["id"], {"PHONE_REQUIRED"}
    )
    assert phone_required["progress"]["phase"] == "phone_required"
    assert phone_required["progress"]["qr_scanned"] is True

    phone = "13800138000"
    sent = client.post(
        f"/profile/imports/{waiting['id']}/phone/code",
        headers=auth_headers,
        json={"phone": phone, "country_code": "+86"},
    )
    assert sent.status_code == 200
    sent_data = sent.json()["data"]
    assert sent_data["status"] == "WAITING_SMS_CODE"
    assert sent_data["phone_masked"] == "138****8000"
    assert sent_data["code_sent"] is True
    assert phone not in sent.text

    phone_status = client.get(
        f"/profile/imports/{waiting['id']}/phone", headers=auth_headers
    )
    assert phone_status.status_code == 200
    assert phone_status.json()["data"]["phone_masked"] == "138****8000"

    wrong_code = "000000"
    rejected = client.post(
        f"/profile/imports/{waiting['id']}/phone/verify",
        headers=auth_headers,
        json={"code": wrong_code},
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "DOUYIN_SMS_CODE_INVALID"
    assert wrong_code not in rejected.text

    accepted = client.post(
        f"/profile/imports/{waiting['id']}/phone/verify",
        headers=auth_headers,
        json={"code": "123456"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["data"]["verified"] is True
    assert accepted.json()["data"]["authenticated_at"] is not None
    _complete(client, auth_headers, waiting["id"])

    with SessionLocal() as db:
        session = db.get(TasteImportSession, waiting["id"])
        persisted = json.dumps(
            {
                "progress": session.progress,
                "analysis": session.analysis_snapshot,
                "result": session.result_snapshot,
                "answers": session.answers,
            },
            ensure_ascii=False,
        )
        assert phone not in persisted
        assert wrong_code not in persisted
        assert "123456" not in persisted


def test_qr_refresh_increments_version(client, auth_headers, monkeypatch):
    monkeypatch.setattr(fake_provider, "_SCAN_DELAY_SECONDS", 60)
    _, data = _create_import(client, auth_headers)
    waiting = _wait_qr(client, auth_headers, data["id"])
    assert waiting["qr_version"] == 0
    qr_before = waiting["qr_image_data_url"]

    response = client.post(
        f"/profile/imports/{data['id']}/qr/refresh", headers=auth_headers
    )
    assert response.status_code == 202

    refreshed = _wait_qr_version(client, auth_headers, data["id"], 1)
    assert refreshed["qr_version"] == 1
    assert refreshed["qr_image_data_url"] != qr_before

    monkeypatch.setattr(fake_provider, "_SCAN_DELAY_SECONDS", 0.15)
    _complete(client, auth_headers, data["id"])


def test_single_active_import_and_force_cancel(client, auth_headers):
    _, first = _create_import(client, auth_headers)
    _wait_qr(client, auth_headers, first["id"])
    _, reused = _create_import(client, auth_headers)
    assert reused["id"] == first["id"]

    _, forced = _create_import(client, auth_headers, force=True)
    assert forced["id"] != first["id"]
    cancelled = client.get(f"/profile/imports/{first['id']}", headers=auth_headers).json()["data"]
    assert cancelled["status"] == "CANCELLED"


def test_cross_user_access_is_404(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    import_id = data["id"]
    other = {"X-User-ID": "u_demo_2"}
    assert client.get(f"/profile/imports/{import_id}", headers=other).status_code == 404
    assert (
        client.get(f"/profile/imports/{import_id}/items", headers=other).status_code == 404
    )
    assert (
        client.post(f"/profile/imports/{import_id}/cancel", headers=other).status_code == 404
    )
    assert (
        client.get(f"/profile/imports/{import_id}/questions", headers=other).status_code == 404
    )
    assert client.get(f"/profile/imports/{import_id}/qr", headers=other).status_code == 404
    assert (
        client.get(f"/profile/imports/{import_id}/qr/image", headers=other).status_code == 404
    )
    assert client.post(f"/profile/imports/{import_id}/verify", headers=other).status_code == 404
    assert client.get(f"/profile/imports/{import_id}/phone", headers=other).status_code == 404
    assert (
        client.post(
            f"/profile/imports/{import_id}/phone/code",
            headers=other,
            json={"phone": "13800138000"},
        ).status_code
        == 404
    )


def test_aweme_dedupe_and_items_pagination(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    _complete(client, auth_headers, data["id"])

    page = client.get(
        f"/profile/imports/{data['id']}/items?cursor=0&limit=50", headers=auth_headers
    ).json()["data"]
    assert len(page["items"]) == 50
    assert page["next_cursor"] == 50
    assert page["has_more"] is True

    items = _dump_all_items(client, auth_headers, data["id"])
    assert len(items) == 260
    ids = [item["aweme_id"] for item in items]
    assert len(set(ids)) == len(ids)
    for item in items:
        assert item["url"].startswith("https://www.douyin.com/")
        assert item["kind"] in {"video", "note"}
        assert "author" in item

    with SessionLocal() as db:
        session = db.get(TasteImportSession, data["id"])
        path = items_path(runtime_dir_for(session.id))
        assert path.is_file()
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 260


def test_max_items_cap_stops_collection(client, auth_headers):
    _, data = _create_import(client, auth_headers, max_items=50)
    done = _wait_status(client, auth_headers, data["id"], {"READY", "FAILED"})
    assert done["status"] == "READY"
    assert done["collection"]["items_collected"] == 50


# --------------------------------------------------------------------------- #
# questions / answers / result
# --------------------------------------------------------------------------- #
def test_questions_and_invalid_answers(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    ready = _complete(client, auth_headers, data["id"])
    # READY status embeds quiz JSON for iOS one-shot load.
    assert ready.get("questions") is not None
    assert ready["questions"]["schema_version"] == "taste-quiz-v1"
    assert ready["questions"]["submit_path"].endswith("/answers")

    questions = _questions(client, auth_headers, data["id"])
    assert questions["schema_version"] == "taste-quiz-v1"
    assert questions["min_answers"] == 3
    assert questions["max_answers"] == 5
    assert questions["intro"]
    assert questions["submit_path"] == f"/profile/imports/{data['id']}/answers"
    assert len(questions["questions"]) in range(3, 6)
    assert questions["candidate_tags"]
    assert questions.get("optional") is True
    for question in questions["questions"]:
        assert question["type"] == "single_choice"
        assert question["required"] is True
        assert len(question["options"]) >= 2
        # Domain refinement questions (not cross-validation personality quizzes).
        assert question["id"].startswith("q_refine_")

    invalid_question = client.post(
        f"/profile/imports/{data['id']}/answers",
        headers=auth_headers,
        json={"answers": [{"question_id": "q_unknown", "option_id": "x"}]},
    )
    assert invalid_question.status_code == 422

    first_q = questions["questions"][0]
    too_few = client.post(
        f"/profile/imports/{data['id']}/answers",
        headers=auth_headers,
        json={"answers": [{"question_id": first_q["id"], "option_id": first_q["options"][0]["id"]}]},
    )
    assert too_few.status_code == 422


def test_answers_produce_ready_result(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    provisional = _complete(client, auth_headers, data["id"])
    assert provisional["result"]["calibrated"] is False
    questions = _questions(client, auth_headers, data["id"])
    payload = _answer_payload(questions)

    response = client.post(f"/profile/imports/{data['id']}/answers", headers=auth_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["meta"].get("refined_with_quiz") is True
    result = response.json()["data"]
    assert result["status"] == "READY"
    assert result["calibrated"] is True
    assert result["interest_facets"]
    # After answers, session no longer embeds pending quiz JSON.
    after = client.get(f"/profile/imports/{data['id']}", headers=auth_headers).json()["data"]
    assert after["result"]["calibrated"] is True
    assert after.get("questions") is None
    assert result["primary_tag"]["key"] in {
        "explorer_builder",
        "ai_practitioner",
        "practical_romantic",
        "strategic_player",
        "knowledge_curator",
        "aesthetic_observer",
        "growth_driver",
    }
    assert 2 <= len(result["secondary_tags"]) <= 3
    assert result["interest_domains"]
    assert set(result["dimensions"]) >= {"openness", "action_orientation"}
    assert result["summary"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["model_version"] == "taste-v2"
    assert result["sample"]["items"] == 260
    assert result["sample"]["calibrated"] is True
    assert result["visibility"] == "members"

    again = client.post(
        f"/profile/imports/{data['id']}/answers", headers=auth_headers, json=payload
    ).json()["data"]
    assert again["primary_tag"]["key"] == result["primary_tag"]["key"]
    assert again["calibrated"] is True

    with SessionLocal() as db:
        session = db.get(TasteImportSession, data["id"])
        assert session.status == "READY"
        assert session.completed_at is not None
        taste = db.get(TasteProfile, "u_demo_1")
        assert taste is not None
        assert taste.primary_tag["key"] == result["primary_tag"]["key"]
        assert taste.sample_summary.get("calibrated") is True
        from onemore.db.models import Profile

        user_profile = db.get(Profile, "u_demo_1")
        assert user_profile is not None
        taste_keys = [key for key in user_profile.self_reported_tags if str(key).startswith("taste:")]
        assert taste_keys
        assert any(str(key).startswith("taste:") for key in user_profile.capability_vector)
        assert user_profile.interest_domains


def test_taste_me_and_profile_me_summary(client, auth_headers):
    before = client.get("/profile/me", headers=auth_headers).json()["data"]
    assert before["taste_profile"] is None
    capability_keys_before = {
        item["key"] for item in before["capabilities"] if item["source"] != "taste"
    }

    _, data = _create_import(client, auth_headers)
    _complete(client, auth_headers, data["id"])

    # Usable profile is available immediately after analysis — before optional quiz.
    taste = client.get("/profile/taste/me", headers=auth_headers).json()["data"]
    assert taste is not None
    assert taste["status"] == "READY"
    assert taste["calibrated"] is False
    assert taste["primary_tag"]["label"]
    assert taste["visibility"] == "members"

    questions = _questions(client, auth_headers, data["id"])
    client.post(
        f"/profile/imports/{data['id']}/answers", headers=auth_headers, json=_answer_payload(questions)
    )
    calibrated = client.get("/profile/taste/me", headers=auth_headers).json()["data"]
    assert calibrated["calibrated"] is True

    me = client.get("/profile/me", headers=auth_headers).json()["data"]
    summary = me["taste_profile"]
    assert summary["primary_tag"]["key"] == calibrated["primary_tag"]["key"]
    assert summary["confidence"] == calibrated["confidence"]
    assert isinstance(summary["secondary_tags"], list)
    assert summary["interest_tags"]
    assert me["init_status"] == before["init_status"]
    # Non-taste capabilities unchanged; taste chips appear as source=taste.
    non_taste = {item["key"] for item in me["capabilities"] if item["source"] != "taste"}
    assert non_taste == capability_keys_before
    taste_caps = [item for item in me["capabilities"] if item["source"] == "taste"]
    assert taste_caps
    assert me["interest_domains"]


def test_taste_tags_feed_matching_and_member_visibility(client, auth_headers):
    """After READY, tags live on Profile and surface for matching + members."""
    from datetime import UTC, datetime, timedelta

    from onemore.db.models import IntentCard, IntentStatus
    from onemore.modules.matching.service import _taste_similarity, match_similar
    from onemore.modules.taste_profile.service import public_interest_tags

    _, data = _create_import(client, auth_headers)
    done = _complete(client, auth_headers, data["id"])
    primary_key = done["result"]["primary_tag"]["key"]

    # Seed a second user with the same fake import path for taste overlap.
    headers_2 = {"X-User-ID": "u_demo_2"}
    _, data2 = _create_import(client, headers_2)
    _complete(client, headers_2, data2["id"])

    with SessionLocal() as db:
        sim = _taste_similarity(db, "u_demo_1", "u_demo_2")
        assert sim > 0.2
        assert public_interest_tags(db, "u_demo_1")
        expires = datetime.now(UTC) + timedelta(days=2)
        source = IntentCard(
            id="intent-taste-1",
            user_id="u_demo_1",
            status=IntentStatus.POOLING.value,
            gathering_type="study",
            mode="similar",
            goal="一起做项目",
            intensity="balanced",
            campus="east",
            min_size=2,
            target_size=3,
            expires_at=expires,
        )
        candidate = IntentCard(
            id="intent-taste-2",
            user_id="u_demo_2",
            status=IntentStatus.POOLING.value,
            gathering_type="study",
            mode="similar",
            goal="一起做项目",
            intensity="balanced",
            campus="east",
            min_size=2,
            target_size=3,
            expires_at=expires,
        )
        db.add(source)
        db.add(candidate)
        db.commit()
        result = match_similar(db, source, candidate)
        assert "taste" in result["dimensions"]
        assert result["dimensions"]["taste"] >= sim - 0.01

    me = client.get("/profile/me", headers=auth_headers).json()["data"]
    assert any(item["source"] == "taste" for item in me["capabilities"])
    assert me["taste_profile"]["primary_tag"]["key"] == primary_key


def test_ai_refresh_returns_unified_taste_result(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    _complete(client, auth_headers, data["id"])
    before = client.get("/profile/taste/me", headers=auth_headers).json()["data"]
    assert before is not None
    assert before["primary_tag"]["key"]

    response = client.post("/profile/taste/me/ai-refresh", headers=auth_headers)
    assert response.status_code == 200
    refreshed = response.json()["data"]
    assert refreshed["status"] == "READY"
    assert refreshed["primary_tag"]["key"] == before["primary_tag"]["key"]
    assert "summary" in refreshed
    assert refreshed["source"] == "douyin"
    # Unified shape shared with GET /taste/me and answers.
    for key in (
        "secondary_tags",
        "interest_domains",
        "interest_facets",
        "matching_hints",
        "calibrated",
        "sample",
    ):
        assert key in refreshed
    again = client.get("/profile/taste/me", headers=auth_headers).json()["data"]
    assert again["primary_tag"]["key"] == refreshed["primary_tag"]["key"]


def test_qr_entry_wait_and_ready_pipeline(client, auth_headers):
    response = client.post(
        "/profile/imports/douyin/qr?wait_seconds=5",
        headers=auth_headers,
        json={"max_items": 0, "force": False},
    )
    assert response.status_code == 202
    qr = response.json()["data"]
    assert qr["import_id"]
    assert qr["status"] in {"PREPARING_QR", "WAITING_SCAN", "READY"}
    import_id = qr["import_id"]
    done = _complete(client, auth_headers, import_id)
    assert done["result"]["primary_tag"]["key"]
    taste = client.get("/profile/taste/me", headers=auth_headers).json()["data"]
    assert taste["primary_tag"]["key"] == done["result"]["primary_tag"]["key"]


def test_delete_douyin_taste(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    _complete(client, auth_headers, data["id"])
    assert client.get("/profile/taste/me", headers=auth_headers).json()["data"] is not None

    response = client.delete("/profile/taste/me/douyin", headers=auth_headers)
    assert response.status_code == 200
    assert client.get("/profile/taste/me", headers=auth_headers).json()["data"] is None
    assert client.get("/profile/me", headers=auth_headers).json()["data"]["taste_profile"] is None

    with SessionLocal() as db:
        sessions = db.scalars(
            select(TasteImportSession).where(TasteImportSession.user_id == "u_demo_1")
        ).all()
        assert sessions == []
        assert db.get(TasteProfile, "u_demo_1") is None
    assert not runtime_dir_for(data["id"]).exists()


# --------------------------------------------------------------------------- #
# cancel / cleanup / privacy
# --------------------------------------------------------------------------- #
def test_cancel_is_idempotent_and_cleans_runtime(client, auth_headers):
    _, data = _create_import(client, auth_headers)
    _wait_qr(client, auth_headers, data["id"])
    first = client.post(f"/profile/imports/{data['id']}/cancel", headers=auth_headers)
    assert first.status_code == 200
    assert first.json()["data"]["status"] == "CANCELLED"
    second = client.post(f"/profile/imports/{data['id']}/cancel", headers=auth_headers)
    assert second.json()["data"]["status"] == "CANCELLED"

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and runtime_dir_for(data["id"]).exists():
        time.sleep(0.05)
    assert not runtime_dir_for(data["id"]).exists()


def test_import_disabled_returns_403(client, auth_headers, monkeypatch):
    monkeypatch.setattr(fake_provider, "_SCAN_DELAY_SECONDS", 60)
    from onemore.core.config import get_settings

    original = get_settings().douyin_import_enabled
    try:
        get_settings().douyin_import_enabled = False
        response = client.post("/profile/imports/douyin", headers=auth_headers, json={})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "DOUYIN_IMPORT_DISABLED"
    finally:
        get_settings().douyin_import_enabled = original


def test_no_cookie_values_in_api_db_or_logs(client, auth_headers, caplog):
    bodies: list[str] = []
    _, data = _create_import(client, auth_headers)
    waiting = _wait_qr(client, auth_headers, data["id"])
    bodies.append(json.dumps(waiting, ensure_ascii=False))
    done = _complete(client, auth_headers, data["id"])
    bodies.append(json.dumps(done, ensure_ascii=False))
    questions = _questions(client, auth_headers, data["id"])
    bodies.append(json.dumps(questions, ensure_ascii=False))
    result = client.post(
        f"/profile/imports/{data['id']}/answers",
        headers=auth_headers,
        json=_answer_payload(questions),
    ).json()
    bodies.append(json.dumps(result, ensure_ascii=False))
    bodies.append(json.dumps(client.get("/profile/taste/me", headers=auth_headers).json()))
    bodies.append(json.dumps(client.get("/profile/me", headers=auth_headers).json()))

    for body in bodies:
        lower = body.lower()
        assert not COOKIE_FLAGS.intersection(lower.split('"'))
        assert "sid_guard" not in lower
    assert not any(flag in caplog.text for flag in COOKIE_FLAGS)

    with SessionLocal() as db:
        sessions = db.scalars(select(TasteImportSession)).all()
        assert sessions
        for session in sessions:
            serialized = json.dumps(
                {
                    "qr": session.qr_image_data_url,
                    "source_profile": session.source_profile,
                    "progress": session.progress,
                    "collection": session.collection_summary,
                    "analysis": session.analysis_snapshot,
                    "result": session.result_snapshot,
                },
                ensure_ascii=False,
            ).lower()
            assert not COOKIE_FLAGS.intersection(serialized.split('"'))


# --------------------------------------------------------------------------- #
# analyzer unit tests (deterministic, no browser)
# --------------------------------------------------------------------------- #
def test_analyzer_is_deterministic_and_has_recent_window():
    raw = []
    for index in range(240):
        description = (
            "AI 教程 手把手 python 智能体"
            if index < 120
            else "摄影调色 氛围感 电影感 教程"
        )
        raw.append(
            {
                "aweme_id": f"753{index}",
                "desc": description,
                "author": {"nickname": f"作者{index % 8}", "uid": f"u{index % 8}", "sec_uid": f"s{index % 8}"},
                "create_time": 1780000000 + index,
                "statistics": {"digg_count": index},
            }
        )
    items = [analyzer.normalize_item(item) for item in raw]
    first = analyzer.analyze_content(items, api_pages=4)
    second = analyzer.analyze_content(items, api_pages=4)
    assert first.content_scores == second.content_scores
    assert first.dimensions == second.dimensions
    assert first.sample_stats["items"] == 240
    assert first.sample_stats["unique_authors"] == 8
    assert first.recent200_domains  # recent window computed from like order
    assert set(first.content_scores) >= {
        "explorer_builder",
        "ai_practitioner",
        "practical_romantic",
        "strategic_player",
        "knowledge_curator",
        "aesthetic_observer",
        "growth_driver",
    }
    questions = analyzer.select_questions(first)
    assert 3 <= len(questions) <= 5
    for question in questions:
        assert question["options"]
        assert question["id"].startswith("q_refine_")
    provisional = analyzer.build_provisional_result(first, items=items, use_llm=False)
    assert provisional["calibrated"] is False
    assert provisional["model_version"] == "taste-v2"
    assert provisional["primary_tag"]["key"]
    refined = analyzer.score_answers(
        first,
        questions,
        [
            {"question_id": q["id"], "option_id": q["options"][0]["id"]}
            for q in questions
        ],
    )
    assert refined["calibrated"] is True
    assert refined["interest_facets"]
    # Quiz refines expression; it should not invent a wholly unrelated primary tag.
    assert refined["primary_tag"]["key"] == provisional["primary_tag"]["key"] or refined[
        "primary_tag"
    ]["key"] in {tag["key"] for tag in provisional["secondary_tags"]}


def test_normalize_item_maps_fields():
    normalized = analyzer.normalize_item(
        {
            "aweme_id": 7531234567890123456,
            "aweme_type": 2,
            "desc": "测试 描述",
            "item_title": "标题",
            "author": {"nickname": "博主", "uid": "1", "sec_uid": "sec1"},
            "create_time": 1780000000,
            "statistics": {"digg_count": 10, "comment_count": 2, "collect_count": 3, "share_count": 1},
            "text_extra": [{"hashtag_name": "AI"}],
            "video_tag": [{"tag_name": "科技"}],
            "video": {"duration": 45000},
        }
    )
    assert normalized["kind"] == "note"
    assert normalized["url"] == "https://www.douyin.com/note/7531234567890123456"
    assert normalized["hashtags"] == ["AI"]
    assert normalized["platform_tags"] == ["科技"]
    assert normalized["duration_seconds"] == 45.0
    assert normalized["statistics"]["likes"] == 10
