#!/usr/bin/env python3
"""Exercise the running FastAPI with the same dev identity used by Simulator."""

from __future__ import annotations

import base64
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("ONEMORE_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
USER_ID = os.environ.get("ONEMORE_DEV_USER_ID", "u_demo_1")
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "logs" / "live-api-smoke.json"
RUN_ID = uuid.uuid4().hex[:12]


class SmokeFailure(RuntimeError):
    pass


def check(value: bool, message: str) -> None:
    if not value:
        raise SmokeFailure(message)


def call(
    method: str,
    path: str,
    *,
    payload: Any | None = None,
    raw: bytes | None = None,
    headers: dict[str, str] | None = None,
    expected: set[int] = {200},
) -> dict[str, Any]:
    request_headers = {"Accept": "application/json", "X-User-ID": USER_ID}
    request_headers.update(headers or {})
    body = raw
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        request_headers["Content-Type"] = "application/json"
    if method not in {"GET", "HEAD"}:
        request_headers.setdefault("Idempotency-Key", f"ios-live-{RUN_ID}-{uuid.uuid4().hex}")
    request = Request(f"{BASE_URL}{path}", data=body, method=method, headers=request_headers)
    try:
        response = urlopen(request, timeout=20)  # noqa: S310 - URL is an explicit local fixture.
        status = response.status
        response_headers = dict(response.headers.items())
        content = response.read()
    except HTTPError as error:
        status = error.code
        response_headers = dict(error.headers.items())
        content = error.read()
    check(status in expected, f"{method} {path}: expected {sorted(expected)}, got {status}: {content[:300]!r}")
    decoded = json.loads(content) if content else None
    request_id = response_headers.get("X-Request-ID") or response_headers.get("x-request-id")
    check(bool(request_id), f"{method} {path}: missing X-Request-ID")
    return {"status": status, "request_id": request_id, "body": decoded}


def data(response: dict[str, Any]) -> Any:
    body = response["body"]
    check(isinstance(body, dict) and "data" in body and "meta" in body, "invalid success envelope")
    return body["data"]


def record(name: str, response: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "status": response["status"],
        "request_id": response["request_id"],
        "facts": facts,
    }


def main() -> int:
    checks: list[dict[str, Any]] = []

    live = call("GET", "/health/live")
    check(live["body"] == {"status": "ok"}, "liveness body mismatch")
    checks.append(record("health_live", live, live["body"]))

    ready = call("GET", "/health/ready")
    check(ready["body"]["status"] == "ready" and ready["body"]["database"] == "ok", "readiness failed")
    checks.append(record("health_ready", ready, ready["body"]))

    today = call("GET", "/today/summary")
    today_data = data(today)
    check(isinstance(today_data, dict), "today summary is not an object")
    checks.append(record("today_summary", today, {"keys": sorted(today_data)}))

    competitions = call("GET", "/competitions")
    competition_rows = data(competitions)
    check(len(competition_rows) == 24, f"expected 24 competitions, got {len(competition_rows)}")
    serialized_competitions = json.dumps(competition_rows, ensure_ascii=False).lower()
    check("demo-innovation-2026" not in serialized_competitions, "demo competition leaked")
    check("2026 校园创新应用大赛" not in serialized_competitions, "legacy demo title leaked")
    checks.append(record("competitions_v1_1", competitions, {"count": 24, "demo_count": 0}))

    compile_response = call(
        "POST",
        "/intent/compile",
        payload={"text": f"周六晚上一起打羽毛球，4人（iOS live {RUN_ID}）"},
    )
    compile_data = data(compile_response)
    check(compile_data["needs_clarification"] is False, "known intent unexpectedly requires clarification")
    card = compile_data["card"]
    check(card["status"] == "Draft" and card["target_size"] == 4, "compiled card mismatch")
    checks.append(record("intent_compile", compile_response, {"card_id": card["id"], "target_size": 4}))

    publish = call("POST", "/intent/publish", payload={"card_id": card["id"]}, expected={201})
    publish_data = data(publish)
    gathering_id = publish_data["gathering_id"]
    check(publish_data["status"] == "Pooling", "published intent did not enter Pooling")
    checks.append(record("intent_publish", publish, {"gathering_id": gathering_id, "status": "Pooling"}))

    gathering = call("GET", f"/gatherings/{gathering_id}")
    gathering_data = data(gathering)
    check(gathering_data["status"] == "Pooling", "gathering status mismatch")
    check(gathering_data.get("participants") in (None, []), "Pooling disclosed participant identities")
    check(gathering_data.get("member_count") is None, "Pooling disclosed member count")
    checks.append(record("gathering_pooling_privacy", gathering, {"participants": None, "member_count": None}))

    leave = call("POST", f"/gatherings/{gathering_id}/leave", payload={})
    leave_data = data(leave)
    check(leave_data["id"] == gathering_id and leave_data["status"] == "Dissolved", "cleanup leave failed")
    checks.append(record("gathering_leave_cleanup", leave, leave_data))

    relations = call("GET", "/relations")
    relation_rows = data(relations)
    check(bool(relation_rows), "demo identity has no relation channel")
    relation = relation_rows[0]
    channel_id = relation["channel_id"]
    relation_json = json.dumps(relation_rows, ensure_ascii=False).lower()
    for forbidden in ("read_at", "online", "typing", "last_seen"):
        check(forbidden not in relation_json, f"relation payload leaked {forbidden}")
    checks.append(record("relations_privacy", relations, {"count": len(relation_rows), "channel_id": channel_id}))

    one_pixel_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    upload = call(
        "POST",
        "/media/images",
        raw=one_pixel_png,
        headers={"Content-Type": "image/png", "X-Filename": "ios-live.png", "X-Image-Width": "1", "X-Image-Height": "1"},
        expected={201},
    )
    asset = data(upload)
    check(asset["content_type"] == "image/png" and asset["byte_count"] == len(one_pixel_png), "image upload mismatch")
    image_message = call(
        "POST",
        f"/channels/{channel_id}/messages",
        payload={"content_type": "image", "image": {"media_id": asset["media_id"], "caption": "iOS 联调像素"}},
        expected={201},
    )
    check(data(image_message)["image"]["media_id"] == asset["media_id"], "typed image message mismatch")
    checks.append(record("image_upload_and_message", image_message, {"media_id": asset["media_id"], "content_type": "image"}))

    location_message = call(
        "POST",
        f"/channels/{channel_id}/messages",
        payload={
            "content_type": "location",
            "location": {"latitude": 22.348, "longitude": 113.598, "label": "珠海校区图书馆", "address": "香洲区大学路2号"},
        },
        expected={201},
    )
    check(data(location_message)["location"]["label"] == "珠海校区图书馆", "typed location message mismatch")
    checks.append(record("location_message", location_message, {"content_type": "location", "one_shot": True}))

    preferences = call("GET", "/me/notification-preferences")
    preference_data = data(preferences)
    patch_payload = {
        "overall_enabled": preference_data["overall_enabled"],
        "calendar_sync_enabled": preference_data["calendar_sync_enabled"],
        "categories": preference_data["categories"],
    }
    preference_patch = call("PATCH", "/me/notification-preferences", payload=patch_payload)
    patched = data(preference_patch)
    check(patched["system_settings_managed_locally"] == [
        "notification_authorization", "calendar_authorization", "focus_mode"
    ], "notification/system boundary mismatch")
    checks.append(record("notification_preferences", preference_patch, {"cross_device": True, "system_boundary": patched["system_settings_managed_locally"]}))

    trust = call("GET", "/trust/me")
    trust_data = data(trust)
    check("level" in trust_data, "trust level missing")
    appeals = call("GET", "/trust/appeals")
    checks.append(record("trust_and_appeals", appeals, {"level": trust_data["level"], "appeal_count": len(data(appeals))}))

    organizer = call("GET", "/organizer/templates", expected={200, 403})
    if organizer["status"] == 200:
        organizer_facts = {"authorized": True, "template_count": len(data(organizer))}
    else:
        error = organizer["body"].get("error", {})
        check(bool(error.get("code")) and bool(error.get("request_id")), "organizer error envelope mismatch")
        organizer_facts = {"authorized": False, "error_code": error["code"]}
    checks.append(record("organizer_trust_gate", organizer, organizer_facts))

    taste = call("POST", "/profile/imports/douyin", payload={"force": True, "max_items": 12}, expected={202})
    taste_data = data(taste)
    check(taste_data["status"] in {"PREPARING_QR", "WAITING_SCAN"}, "taste import did not start")
    cancel = call("POST", f"/profile/imports/{taste_data['id']}/cancel", payload={})
    check(data(cancel)["status"] == "CANCELLED", "taste import cleanup failed")
    checks.append(record("taste_import_start_cancel", cancel, {"import_id": taste_data["id"], "status": "CANCELLED"}))

    report = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "timestamp": datetime.now(UTC).isoformat(),
        "base_url": BASE_URL,
        "user_id": USER_ID,
        "result": "passed",
        "check_count": len(checks),
        "checks": checks,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS: {len(checks)} live API checks -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {
            "schema_version": 1,
            "run_id": RUN_ID,
            "timestamp": datetime.now(UTC).isoformat(),
            "base_url": BASE_URL,
            "user_id": USER_ID,
            "result": "failed",
            "error": f"{type(error).__name__}: {error}",
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n")
        print(f"FAIL: {failure['error']} -> {OUTPUT}", file=sys.stderr)
        raise
