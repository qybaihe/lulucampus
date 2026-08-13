from __future__ import annotations

from onemore.core.database import SessionLocal, create_schema
from onemore.db.peer_overlap import apply_peer_overlap_template


def main() -> None:
    create_schema()
    with SessionLocal() as db:
        result = apply_peer_overlap_template(db)
    print("peer overlap template applied")
    print("cast", ",".join(result["cast_ids"]))
    print("live", ",".join(result["live_ids"]) or "(none)")
    print("courses", ",".join(result["courses"]))
    print("gym", ",".join(result["gym"]))


if __name__ == "__main__":
    main()
