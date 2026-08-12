from __future__ import annotations

from onemore.core.database import SessionLocal, create_schema
from onemore.db.seed import seed_demo_data


def main() -> None:
    create_schema()
    with SessionLocal() as db:
        seed_demo_data(db)
    print("Demo data seeded. Use X-User-ID: u_demo_1")


if __name__ == "__main__":
    main()
