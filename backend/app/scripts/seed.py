"""
Seed script — creates the field and lots required by the CSV fixtures.

Static IDs match those in tests/fixtures/generate.py so that the CSV files
can be uploaded immediately after running this script.

Usage:
    uv run python -m app.scripts.seed
"""
import asyncio

from sqlalchemy import text

from app.core.database import async_session_factory

FIELD_ID = "c0ffee00-0000-0000-0000-000000000001"

LOT_IDS = [f"10000000-0000-0000-0000-{i:012d}" for i in range(1, 11)]
LOT_NAMES = [f"Lote {i}" for i in range(1, 11)]


async def seed() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(
                text("INSERT INTO fields (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING"),
                {"id": FIELD_ID, "name": "Campo Principal"},
            )
            print("✓ Field created")

            for lot_id, lot_name in zip(LOT_IDS, LOT_NAMES):
                await session.execute(
                    text("INSERT INTO lots (id, name, field_id) VALUES (:id, :name, :fid) ON CONFLICT (id) DO NOTHING"),
                    {"id": lot_id, "name": lot_name, "fid": FIELD_ID},
                )
            print(f"✓ {len(LOT_IDS)} lots created")

    print("Seed done. Upload tests/fixtures/animals.csv via POST /animals/bulk")


if __name__ == "__main__":
    asyncio.run(seed())
