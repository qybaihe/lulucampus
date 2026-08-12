from __future__ import annotations

from onemore.core.database import SessionLocal, create_schema
from onemore.db.seed import seed_demo_data


def main() -> None:
    create_schema()
    with SessionLocal() as db:
        seed_demo_data(db)
    print("Demo cast seeded. X-User-ID: u_demo_1 (林予安) … u_demo_6 (何屿)")
    print("Phone login: 13900001001–006 / cast-onemore")


if __name__ == "__main__":
    main()
