from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet

from onemore.core.config import get_settings
from onemore.core.errors import AppError

USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class VaultManager:
    SESSION_FILES = {
        "session.json",
        "jwxt-session.json",
        "libic-session.json",
        "gym-session.json",
        "gym-auth.json",
        "explore-session.json",
        "career-session.json",
        "matrix-session.json",
    }

    FILES_BY_GRANT = {
        "timetable": {"session.json", "jwxt-session.json"},
        "curriculum": {"session.json", "jwxt-session.json"},
        "enrollment": {"session.json", "jwxt-session.json", "matrix-session.json"},
        "agent_booking": {
            "libic-session.json",
            "gym-session.json",
            "gym-auth.json",
            "explore-session.json",
        },
    }

    def __init__(self, root: Path | None = None, master_key: str | None = None) -> None:
        settings = get_settings()
        self.root = (root or settings.vault_root).resolve()
        material = master_key or settings.vault_master_key or "local-development-only"
        key = base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest())
        self.cipher = Fernet(key)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _validate_user_id(self, user_id: str) -> str:
        if not USER_ID_PATTERN.fullmatch(user_id):
            raise AppError("INVALID_USER_ID", "用户标识格式错误", 400)
        return user_id

    def user_root(self, user_id: str) -> Path:
        safe = self._validate_user_id(user_id)
        path = self.root / f"u_{safe}"
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    def read_meta(self, user_id: str) -> dict:
        path = self.user_root(user_id) / "_meta.json"
        if not path.exists():
            return {"user_id": user_id, "grants": {}, "sessions": {}, "revoked_at": None}
        return json.loads(path.read_text(encoding="utf-8"))

    def write_meta(self, user_id: str, meta: dict) -> None:
        path = self.user_root(user_id) / "_meta.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(path)

    def set_grant(self, user_id: str, scope: str, granted: bool) -> None:
        meta = self.read_meta(user_id)
        now = datetime.now(UTC).isoformat()
        meta.setdefault("grants", {})[scope] = {
            "granted": granted,
            "at": now if granted else None,
        }
        if not granted:
            meta["revoked_at"] = now
            names = self.FILES_BY_GRANT.get(scope, set())
            for encrypted in self.user_root(user_id).glob("*.enc"):
                relative = self._relative_from_encrypted(encrypted.name)
                if relative and Path(relative).name in names:
                    encrypted.unlink(missing_ok=True)
        self.write_meta(user_id, meta)

    def update_session_health(
        self, user_id: str, subsystem: str, healthy: bool, error_category: str | None
    ) -> None:
        meta = self.read_meta(user_id)
        meta.setdefault("sessions", {})[subsystem] = {
            "healthy": healthy,
            "last_checked_at": datetime.now(UTC).isoformat(),
            "error_category": error_category,
        }
        self.write_meta(user_id, meta)

    def purge_user(self, user_id: str) -> None:
        safe = self._validate_user_id(user_id)
        shutil.rmtree(self.root / f"u_{safe}", ignore_errors=True)

    @staticmethod
    def _encrypted_name(relative: str) -> str:
        encoded = base64.urlsafe_b64encode(relative.encode()).decode("ascii").rstrip("=")
        return f"p_{encoded}.enc"

    @staticmethod
    def _relative_from_encrypted(name: str) -> str | None:
        if name.startswith("p_") and name.endswith(".enc"):
            encoded = name[2:-4]
            try:
                return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
            except (ValueError, UnicodeDecodeError):
                return None
        if name.endswith(".enc"):
            return name.removesuffix(".enc")
        return None

    @contextmanager
    def mounted(self, user_id: str) -> Iterator[Path]:
        persistent = self.user_root(user_id)
        mount = Path(tempfile.mkdtemp(prefix=f"onemore-{user_id}-"))
        mount.chmod(0o700)
        mount_root = mount.resolve()
        try:
            for encrypted in persistent.glob("*.enc"):
                relative = self._relative_from_encrypted(encrypted.name)
                if not relative:
                    continue
                plain = mount_root / relative
                if mount_root not in plain.resolve().parents:
                    continue
                plain.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                plain.write_bytes(self.cipher.decrypt(encrypted.read_bytes()))
                plain.chmod(0o600)
            yield mount
            self.persist_session_files(user_id, mount)
        finally:
            shutil.rmtree(mount, ignore_errors=True)

    def persist_session_files(self, user_id: str, source_root: Path) -> None:
        """Encrypt an authenticated CLI mount into a stable user's vault.

        Login starts in a provisional vault because the campus subject is not
        known until CAS succeeds.  Once the subject is pseudonymized and bound
        to the stable account, this method atomically copies only the allowlisted
        session files into that account's encrypted store.
        """

        persistent = self.user_root(user_id)
        root = source_root.resolve()
        for plain in source_root.rglob("*"):
            if (
                not plain.is_file()
                or plain.is_symlink()
                or plain.name not in self.SESSION_FILES
                or plain.stat().st_size > 10 * 1024 * 1024
            ):
                continue
            resolved = plain.resolve()
            if root not in resolved.parents:
                continue
            relative = resolved.relative_to(root).as_posix()
            encrypted = persistent / self._encrypted_name(relative)
            encrypted.write_bytes(self.cipher.encrypt(plain.read_bytes()))
            encrypted.chmod(0o600)
            if relative == plain.name:
                legacy = persistent / f"{plain.name}.enc"
                if legacy != encrypted:
                    legacy.unlink(missing_ok=True)


vault_manager = VaultManager()
