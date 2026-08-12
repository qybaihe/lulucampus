from __future__ import annotations

import argparse
from pathlib import Path

from onemore.core.database import SessionLocal, create_schema
from onemore.db.seed import seed_reference_data
from onemore.modules.competitions.service import ingest_snapshot_path


def main() -> None:
    parser = argparse.ArgumentParser(description="摄取已核验赛事快照")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    create_schema()
    with SessionLocal() as db:
        seed_reference_data(db)
        result = ingest_snapshot_path(db, args.path)
    print(result)


if __name__ == "__main__":
    main()
