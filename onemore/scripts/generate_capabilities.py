from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from onemore.core.config import get_settings
from onemore.hermes.catalog import CATALOG
from onemore.hermes.schemas import ActionName

HELP_COMMANDS: dict[ActionName, tuple[str, ...]] = {
    ActionName.TIMETABLE_FETCH_TERM: ("jwxt", "timetable"),
    ActionName.TIMETABLE_TODAY: ("today",),
    ActionName.TIMETABLE_SECTION_TIMES: ("jwxt", "section-times"),
    ActionName.ASSIGNMENT_LIST_UNFINISHED: ("matrix", "assignments", "list"),
    ActionName.ROOM_AVAILABLE: ("libic", "available"),
    ActionName.ROOM_ROOM_TYPES: ("libic", "room-types"),
    ActionName.ROOM_RESERVE_PREVIEW: ("libic", "reserve"),
    ActionName.ROOM_RESERVE_COMMIT: ("libic", "reserve"),
    ActionName.GYM_AVAILABLE: ("gym", "available"),
    ActionName.GYM_BOOK_PREVIEW: ("gym", "book"),
    ActionName.GYM_BOOK_COMMIT: ("gym", "book"),
    ActionName.SEMINAR_LIST: ("explore", "seminar", "list"),
    ActionName.SEMINAR_RESERVE_PREVIEW: ("explore", "seminar", "reserve"),
    ActionName.SEMINAR_RESERVE_COMMIT: ("explore", "seminar", "reserve"),
    ActionName.CAREER_TEACHIN_LIST: ("career", "teachin", "list"),
    ActionName.CAREER_JOBFAIR_LIST: ("career", "jobfair", "list"),
    ActionName.TRANSIT_BUS: ("bus",),
    ActionName.TRANSIT_QIGUAN: ("qg", "list"),
}


def generate(output: Path) -> dict:
    settings = get_settings()
    entries: dict[str, dict] = {}
    cache: dict[tuple[str, ...], tuple[int, str]] = {}
    for action in ActionName:
        command = HELP_COMMANDS[action]
        if command not in cache:
            completed = subprocess.run(
                [settings.sysu_cli, *command, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False,
            )
            cache[command] = (completed.returncode, completed.stdout + completed.stderr)
        returncode, help_text = cache[command]
        definition = CATALOG[action]
        entries[action.value] = {
            "command": list(command),
            "tier": definition.tier.value,
            "subsystem": definition.subsystem,
            "write": definition.is_write,
            "required_grant": definition.required_grant,
            "required_trust_level": definition.required_trust_level,
            "supports_state_dir": definition.supports_state_dir,
            "help_verified": returncode == 0 and "Usage:" in help_text,
            "help_sha256": hashlib.sha256(help_text.encode()).hexdigest(),
        }
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "cli": settings.sysu_cli,
        "actions": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "hermes" / "capabilities.json"
    manifest = generate(output)
    failed = [name for name, item in manifest["actions"].items() if not item["help_verified"]]
    print(f"Wrote {len(manifest['actions'])} actions to {output}")
    if failed:
        raise SystemExit(f"CLI help verification failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
