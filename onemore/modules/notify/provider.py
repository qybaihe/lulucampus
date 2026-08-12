from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from onemore.core.config import Settings, get_settings


@dataclass(frozen=True)
class PushProviderResult:
    status_code: int
    reason: str | None = None
    message_id: str | None = None

    @property
    def delivered(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def invalid_token(self) -> bool:
        return self.status_code == 410 or self.reason in {
            "BadDeviceToken",
            "DeviceTokenNotForTopic",
            "Unregistered",
        }


class PushProvider(Protocol):
    def send(self, token: str, payload: dict) -> PushProviderResult: ...


class FakePushProvider:
    """Deterministic provider used by local and test environments.

    Reserved token prefixes exercise provider lifecycle without logging or
    exposing the token: ``fake:gone:`` emulates APNs 410 and ``fake:error:`` a
    transient 503. Every other token is accepted.
    """

    def send(self, token: str, payload: dict) -> PushProviderResult:
        del payload
        if token.startswith("fake:gone:"):
            return PushProviderResult(410, "Unregistered", "fake-unregistered")
        if token.startswith("fake:error:"):
            return PushProviderResult(503, "ServiceUnavailable", "fake-retry")
        return PushProviderResult(200, message_id="fake-delivered")


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


class APNsPushProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._cached_jwt: tuple[int, str] | None = None

    def _private_key_bytes(self) -> bytes:
        configured = self.settings.apns_private_key
        if configured is None:
            raise RuntimeError("APNs private key is not configured")
        if configured.startswith("@"):
            return Path(configured[1:]).read_bytes()
        return configured.replace("\\n", "\n").encode()

    def _authorization_token(self) -> str:
        now = int(time.time())
        if self._cached_jwt is not None and now - self._cached_jwt[0] < 50 * 60:
            return self._cached_jwt[1]
        if self.settings.apns_key_id is None or self.settings.apns_team_id is None:
            raise RuntimeError("APNs key id and team id are not configured")
        header = _base64url(
            json.dumps(
                {"alg": "ES256", "kid": self.settings.apns_key_id},
                separators=(",", ":"),
            ).encode()
        )
        claims = _base64url(
            json.dumps(
                {"iss": self.settings.apns_team_id, "iat": now},
                separators=(",", ":"),
            ).encode()
        )
        unsigned = f"{header}.{claims}".encode()
        key = serialization.load_pem_private_key(self._private_key_bytes(), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey):
            raise RuntimeError("APNs provider key must be an EC private key")
        der_signature = key.sign(unsigned, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der_signature)
        signature = _base64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        token = f"{header}.{claims}.{signature}"
        self._cached_jwt = (now, token)
        return token

    def send(self, token: str, payload: dict) -> PushProviderResult:
        topic = self.settings.apns_topic
        if topic is None:
            raise RuntimeError("APNs topic is not configured")
        host = (
            "https://api.push.apple.com"
            if self.settings.apns_environment == "production"
            else "https://api.sandbox.push.apple.com"
        )
        try:
            with httpx.Client(
                http2=True, timeout=self.settings.apns_timeout_seconds
            ) as client:
                response = client.post(
                    f"{host}/3/device/{token}",
                    headers={
                        "authorization": f"bearer {self._authorization_token()}",
                        "apns-topic": topic,
                        "apns-push-type": "alert",
                        "apns-priority": "10",
                        "apns-expiration": "0",
                    },
                    json=payload,
                )
        except httpx.HTTPError:
            return PushProviderResult(503, "NetworkUnavailable")
        reason: str | None = None
        if response.content:
            try:
                decoded = response.json()
                if isinstance(decoded, dict) and isinstance(decoded.get("reason"), str):
                    reason = decoded["reason"]
            except ValueError:
                reason = "InvalidProviderResponse"
        return PushProviderResult(
            response.status_code,
            reason=reason,
            message_id=response.headers.get("apns-id"),
        )


def get_push_provider(settings: Settings | None = None) -> PushProvider:
    configured = settings or get_settings()
    if configured.push_mode == "apns":
        return APNsPushProvider(configured)
    return FakePushProvider()
