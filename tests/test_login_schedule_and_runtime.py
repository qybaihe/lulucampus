from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from onemore.core.config import get_settings
from onemore.core.database import SessionLocal
from onemore.core.errors import AppError
from onemore.db.models import (
    Enrollment,
    LoginSession,
    LoginStatus,
    TrustLevel,
    TrustProfile,
    User,
)
from onemore.hermes.login import LoginOrchestrator
from onemore.hermes.schemas import ActionName
from onemore.hermes.vault import VaultManager
from onemore.modules.identity import service as identity_service
from onemore.modules.identity.service import create_login_session
from onemore.modules.schedule.service import etl_term_timetable


def test_signed_access_token_after_success(client):
    created = client.post("/auth/session", json={}).json()["data"]
    secret = created["redemption_token"]
    redemption_header = {"X-Login-Redemption": secret}
    assert created["access_token"] is None
    client.post(
        f"/auth/session/{created['id']}/demo-complete", headers=redemption_header
    )
    polled = client.get(
        f"/auth/session/{created['id']}", headers=redemption_header
    ).json()["data"]
    assert polled["access_token"] is None
    redeemed = client.post(
        f"/auth/session/{created['id']}/redeem",
        headers={"Idempotency-Key": f"login-redeem-{created['id']}"},
        json={"redemption_token": secret},
    )
    token = redeemed.json()["data"]["access_token"]
    assert token.startswith("om1.")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    replayed = client.post(
        f"/auth/session/{created['id']}/redeem",
        headers={"Idempotency-Key": f"login-redeem-{created['id']}"},
        json={"redemption_token": secret},
    )
    assert replayed.status_code == 200
    assert replayed.json()["data"]["access_token"] == token
    assert (
        client.post(
            f"/auth/session/{created['id']}/redeem",
            headers={"Idempotency-Key": "different-redemption-operation"},
            json={"redemption_token": secret},
        ).status_code
        == 409
    )
    replayed_poll = client.get(
        f"/auth/session/{created['id']}", headers=redemption_header
    ).json()["data"]
    assert replayed_poll["access_token"] is None


def test_login_success_expiry_cancel_and_atomic_concurrent_redemption(client):
    expired = client.post("/auth/session", json={}).json()["data"]
    expired_header = {"X-Login-Redemption": expired["redemption_token"]}
    client.post(
        f"/auth/session/{expired['id']}/demo-complete", headers=expired_header
    )
    with SessionLocal() as db:
        row = db.get(LoginSession, expired["id"])
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    timed_out = client.get(
        f"/auth/session/{expired['id']}", headers=expired_header
    )
    assert timed_out.json()["data"]["status"] == "TIMEOUT"
    assert (
        client.post(
            f"/auth/session/{expired['id']}/redeem",
            headers={"Idempotency-Key": f"login-redeem-{expired['id']}"},
            json={"redemption_token": expired["redemption_token"]},
        ).status_code
        == 410
    )

    cancelled = client.post("/auth/session", json={}).json()["data"]
    cancelled_header = {"X-Login-Redemption": cancelled["redemption_token"]}
    client.post(
        f"/auth/session/{cancelled['id']}/demo-complete", headers=cancelled_header
    )
    stopped = client.post(
        f"/auth/session/{cancelled['id']}/cancel", headers=cancelled_header
    )
    assert stopped.json()["data"]["status"] == "CANCELLED"
    assert (
        client.post(
            f"/auth/session/{cancelled['id']}/redeem",
            headers={"Idempotency-Key": f"login-redeem-{cancelled['id']}"},
            json={"redemption_token": cancelled["redemption_token"]},
        ).status_code
        == 409
    )

    concurrent = client.post("/auth/session", json={}).json()["data"]
    concurrent_header = {"X-Login-Redemption": concurrent["redemption_token"]}
    client.post(
        f"/auth/session/{concurrent['id']}/demo-complete", headers=concurrent_header
    )

    operation_keys = ["concurrent-redemption-one", "concurrent-redemption-two"]

    def redeem_once(operation_key: str) -> str:
        with SessionLocal() as db:
            try:
                return identity_service.redeem_login_session(
                    db,
                    concurrent["id"],
                    concurrent["redemption_token"],
                    operation_key,
                )
            except AppError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(redeem_once, operation_keys))
    assert sum(item.startswith("om1.") for item in results) == 1
    assert results.count("LOGIN_ALREADY_REDEEMED") == 1
    assert (
        client.get(f"/auth/session/{concurrent['id']}").status_code == 422
    ), "session id alone cannot poll or mint a token"


def test_real_login_orchestrator_publishes_qr_and_encrypts_session(tmp_path, monkeypatch):
    cli = tmp_path / "fake-sysu"
    cli.write_text(
        """#!/usr/bin/env python3
import pathlib, sys, time
state = pathlib.Path(sys.argv[sys.argv.index('--state-dir') + 1])
(state / 'qr').mkdir(parents=True)
(state / 'qr' / 'workwechat-login.png').write_bytes(b'PNG')
time.sleep(0.3)
(state / 'session.json').write_text('{"cookies":[{"key":"username_test","value":"20260001","domain":"sysu.edu.cn"}],"cookie":"secret"}')
print('ok')
""",
        encoding="utf-8",
    )
    cli.chmod(0o700)
    settings = get_settings().model_copy(
        update={"sysu_cli": str(cli), "executor_login_timeout_seconds": 2}
    )
    import onemore.hermes.login as login_module

    test_vault = VaultManager(root=tmp_path / "vault", master_key="test-key")
    monkeypatch.setattr(login_module, "get_settings", lambda: settings)
    monkeypatch.setattr(login_module, "vault_manager", test_vault)
    orchestrator = LoginOrchestrator()
    orchestrator.poll_interval_seconds = 0.02

    with SessionLocal() as db:
        login, _ = create_login_session(db)
        session_id = login.id
        user_id = login.user_id
    orchestrator.run(session_id)

    with SessionLocal() as db:
        login = db.get(LoginSession, session_id)
        user = db.get(User, user_id)
        assert login is not None and login.status == LoginStatus.SUCCESS.value
        assert login.qr_image_data_url == "data:image/png;base64,UE5H"
        assert user is not None and user.verified_at is not None
    encrypted_files = list(test_vault.user_root(user_id).glob("*.enc"))
    assert len(encrypted_files) == 1
    encrypted = encrypted_files[0]
    assert b"secret" not in encrypted.read_bytes()


def test_campus_identity_is_stable_across_login_sessions_and_isolated_by_subject():
    with SessionLocal() as db:
        first, _ = create_login_session(db)
        first = identity_service.complete_fake_login(db, first.id, "20260001")
        stable_user_id = first.user_id
        stable_user = db.get(User, stable_user_id)
        assert stable_user is not None
        stable_user.display_name = "跨设备保留"
        trust = db.get(TrustProfile, stable_user_id)
        assert trust is not None
        trust.level = TrustLevel.T4.value
        db.commit()

        second, _ = create_login_session(db)
        second = identity_service.complete_fake_login(db, second.id, "20260001")
        assert second.user_id == stable_user_id
        assert db.get(User, stable_user_id).display_name == "跨设备保留"
        assert db.get(TrustProfile, stable_user_id).level == TrustLevel.T4.value

        different, _ = create_login_session(db)
        different = identity_service.complete_fake_login(db, different.id, "20260002")
        assert different.user_id != stable_user_id
        assert db.get(User, different.user_id).netid_hash != db.get(
            User, stable_user_id
        ).netid_hash
        assert (
            db.scalar(
                select(User).where(User.account_status == "pending_identity")
            )
            is None
        )


def test_default_fake_scan_resumes_exact_active_user_without_trust_downgrade(client):
    with SessionLocal() as db:
        trust = db.get(TrustProfile, "u_demo_1")
        assert trust is not None
        trust.level = TrustLevel.T3.value
        db.commit()

    created = client.post(
        "/auth/session",
        json={"resume_user_id": "u_demo_1", "device_install_id": "resume-device"},
    ).json()["data"]
    redemption = {"X-Login-Redemption": created["redemption_token"]}
    completed = client.post(
        f"/auth/session/{created['id']}/demo-complete", headers=redemption
    )
    assert completed.status_code == 200, completed.text
    polled = client.get(f"/auth/session/{created['id']}", headers=redemption)
    assert polled.json()["data"]["user_id"] == "u_demo_1"
    with SessionLocal() as db:
        assert db.get(TrustProfile, "u_demo_1").level == TrustLevel.T3.value


def test_real_login_fails_closed_without_a_stable_campus_subject(tmp_path, monkeypatch):
    cli = tmp_path / "fake-sysu-no-subject"
    cli.write_text(
        """#!/usr/bin/env python3
import pathlib, sys
state = pathlib.Path(sys.argv[sys.argv.index('--state-dir') + 1])
(state / 'qr').mkdir(parents=True)
(state / 'qr' / 'workwechat-login.png').write_bytes(b'PNG')
(state / 'session.json').write_text('{"cookies":[{"key":"SESSION","value":"opaque","domain":"cas.sysu.edu.cn"}]}')
""",
        encoding="utf-8",
    )
    cli.chmod(0o700)
    settings = get_settings().model_copy(
        update={"sysu_cli": str(cli), "executor_login_timeout_seconds": 2}
    )
    import onemore.hermes.login as login_module

    test_vault = VaultManager(root=tmp_path / "vault-no-subject", master_key="test-key")
    monkeypatch.setattr(login_module, "get_settings", lambda: settings)
    monkeypatch.setattr(login_module, "vault_manager", test_vault)
    orchestrator = LoginOrchestrator()
    orchestrator.poll_interval_seconds = 0.02

    with SessionLocal() as db:
        login, _ = create_login_session(db)
        session_id = login.id
    orchestrator.run(session_id)
    with SessionLocal() as db:
        login = db.get(LoginSession, session_id)
        assert login is not None
        assert login.status == LoginStatus.FAILED.value
        assert login.error_category == "identity_unavailable"


def test_real_login_is_not_redeemable_when_stable_vault_persistence_fails(
    tmp_path, monkeypatch
):
    cli = tmp_path / "fake-sysu-vault-failure"
    cli.write_text(
        """#!/usr/bin/env python3
import pathlib, sys
state = pathlib.Path(sys.argv[sys.argv.index('--state-dir') + 1])
(state / 'qr').mkdir(parents=True)
(state / 'qr' / 'workwechat-login.png').write_bytes(b'PNG')
(state / 'session.json').write_text('{"cookies":[{"key":"username_test","value":"20269999","domain":"sysu.edu.cn"}]}')
""",
        encoding="utf-8",
    )
    cli.chmod(0o700)
    settings = get_settings().model_copy(
        update={"sysu_cli": str(cli), "executor_login_timeout_seconds": 2}
    )
    import onemore.hermes.login as login_module

    test_vault = VaultManager(root=tmp_path / "vault-failure", master_key="test-key")

    def fail_persistence(user_id, source_root):
        raise OSError("simulated encrypted vault failure")

    monkeypatch.setattr(test_vault, "persist_session_files", fail_persistence)
    monkeypatch.setattr(login_module, "get_settings", lambda: settings)
    monkeypatch.setattr(login_module, "vault_manager", test_vault)
    orchestrator = LoginOrchestrator()
    orchestrator.poll_interval_seconds = 0.02

    with SessionLocal() as db:
        login, redemption_token = create_login_session(db)
        session_id = login.id
        provisional_user_id = login.user_id
    orchestrator.run(session_id)
    with SessionLocal() as db:
        login = db.get(LoginSession, session_id)
        assert login is not None
        assert login.status == LoginStatus.FAILED.value
        with pytest.raises(AppError) as raised:
            identity_service.redeem_login_session(
                db, session_id, redemption_token, "vault-failure-redeem"
            )
        assert raised.value.code == "LOGIN_NOT_READY"
    assert list(test_vault.user_root(provisional_user_id).glob("*.enc")) == []


def test_timetable_etl_persists_class_level_without_scores():
    payload = {
        "schoolYear": "2026-1",
        "occurrences": [
            {
                "courseName": "软件工程",
                "sourceGroupKey": "SE-CLASS-A",
                "weekly": 1,
                "startAt": "2026-08-12T10:00:00+08:00",
                "endAt": "2026-08-12T11:40:00+08:00",
                "location": "珠海校区教学楼",
                "raw": {"courseCode": "SE101", "teachingClassId": "SE101-A"},
            }
        ],
    }
    with SessionLocal() as db:
        result = etl_term_timetable(db, "u_demo_1", payload)
        enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == "u_demo_1"))
        assert result["enrollments_imported"] == 1
        assert result["windows_generated"] > 0
        assert enrollment is not None
        assert enrollment.class_code == "SE101-A"
        assert {"grade", "score", "gpa"}.isdisjoint(enrollment.__table__.columns.keys())


def test_today_summary_only_includes_local_day_and_hides_jwxt_codes(client, auth_headers):
    """Home timeline must be a real day axis: today only, no jwxt hashes as titles."""
    from datetime import UTC, datetime, timedelta
    from zoneinfo import ZoneInfo

    shanghai = ZoneInfo("Asia/Shanghai")
    local_today = datetime.now(shanghai).date()
    today_start = datetime.combine(local_today, datetime.min.time(), shanghai)
    tomorrow_start = today_start + timedelta(days=1)
    payload = {
        "schoolYear": "2026-1",
        "occurrences": [
            {
                "courseName": "本(专必)计算机网络",
                "sourceGroupKey": "jwxt:8bb70e71af63aff1",
                "weekly": 1,
                "startAt": (today_start + timedelta(hours=10, minutes=10)).isoformat(),
                "endAt": (today_start + timedelta(hours=11, minutes=50)).isoformat(),
                "location": "珠海校区-教学大楼-珠海 E301",
                "raw": {"teachingClassId": "2001197074881376257"},
            },
            {
                "courseName": "本(专必)操作系统原理",
                "sourceGroupKey": "jwxt:747ea6e9f3236a4a",
                "weekly": 1,
                "startAt": (tomorrow_start + timedelta(hours=10, minutes=10)).isoformat(),
                "endAt": (tomorrow_start + timedelta(hours=11, minutes=50)).isoformat(),
                "location": "珠海校区-教学大楼-珠海 E301",
                "raw": {"teachingClassId": "2001186904692420609"},
            },
        ],
    }
    with SessionLocal() as db:
        etl_term_timetable(db, "u_demo_1", payload)

    response = client.get("/today/summary", headers=auth_headers)
    assert response.status_code == 200
    timeline = response.json()["data"]["timeline"]
    course_items = [item for item in timeline if item.get("kind") == "course"]
    titles = {item["title"] for item in course_items}
    assert "本(专必)计算机网络" in titles
    assert "本(专必)操作系统原理" not in titles
    for item in course_items:
        assert item.get("course_code") in (None, "")
        assert item.get("class_code") in (None, "")
        assert "jwxt:" not in (item.get("title") or "")
        assert item.get("time_label")
        assert "–" in item["time_label"] or "-" in item["time_label"]
        start = datetime.fromisoformat(item["start_at"].replace("Z", "+00:00")).astimezone(
            shanghai
        )
        assert start.date() == local_today


def test_capability_manifest_matches_action_schema():
    manifest_path = Path("onemore/hermes/capabilities.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert set(manifest["actions"]) == {action.value for action in ActionName}
    assert all(item["help_verified"] for item in manifest["actions"].values())


def test_vault_persists_nested_cli_home_and_revokes_scope(tmp_path):
    vault = VaultManager(root=tmp_path / "nested-vault", master_key="nested-key")
    with vault.mounted("nested_user") as mount:
        state = mount / ".sysu-anything"
        state.mkdir()
        (state / "matrix-session.json").write_text('{"token":"private"}')
    encrypted = list(vault.user_root("nested_user").glob("*.enc"))
    assert len(encrypted) == 1
    assert b"private" not in encrypted[0].read_bytes()
    with vault.mounted("nested_user") as mount:
        restored = mount / ".sysu-anything" / "matrix-session.json"
        assert restored.read_text() == '{"token":"private"}'
    vault.set_grant("nested_user", "enrollment", False)
    assert list(vault.user_root("nested_user").glob("*.enc")) == []
