"""Manually tick the demo-cast driver once (same path as Celery beat)."""

from __future__ import annotations

import json

from onemore.core.database import SessionLocal
from onemore.modules.cast_driver.service import tick


def main() -> None:
    with SessionLocal() as db:
        result = tick(db, force=True, enabled=True)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
