#!/usr/bin/env python3
"""Import local ~/.sysu-anything session files into an OneMore Hermes vault."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from onemore.hermes.vault import VaultManager

DEFAULT_FILES = [
    "session.json",
    "jwxt-session.json",
    "libic-session.json",
    "gym-session.json",
    "gym-auth.json",
    "explore-session.json",
    "career-session.json",
    "matrix-session.json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", default="u_demo_1")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / ".sysu-anything",
        help="sysu-anything state directory",
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        default=Path("./vaults"),
        help="OneMore vault root",
    )
    parser.add_argument(
        "--master-key",
        default="local-development-only",
        help="Must match ONEMORE_VAULT_MASTER_KEY",
    )
    parser.add_argument(
        "--grants",
        nargs="*",
        default=["timetable", "curriculum", "enrollment", "agent_booking"],
    )
    args = parser.parse_args()

    source: Path = args.source.expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"source state dir missing: {source}")

    vault = VaultManager(root=args.vault_root.resolve(), master_key=args.master_key)
    with tempfile.TemporaryDirectory(prefix="onemore-import-") as tmp:
        mount = Path(tmp)
        copied: list[str] = []
        for name in DEFAULT_FILES:
            src = source / name
            if not src.is_file():
                continue
            dest = mount / name
            shutil.copy2(src, dest)
            dest.chmod(0o600)
            copied.append(name)
        if not copied:
            raise SystemExit(f"no allowlisted session files found under {source}")
        vault.persist_session_files(args.user_id, mount)

    for scope in args.grants:
        vault.set_grant(args.user_id, scope, True)

    meta = vault.read_meta(args.user_id)
    encrypted = sorted(path.name for path in vault.user_root(args.user_id).glob("*.enc"))
    print(f"imported_user={args.user_id}")
    print(f"copied={copied}")
    print(f"encrypted={encrypted}")
    print(f"grants={meta.get('grants')}")


if __name__ == "__main__":
    main()
