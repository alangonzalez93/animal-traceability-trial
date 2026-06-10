from pathlib import Path

import pytest
from sqlalchemy import text

from tests.fixtures.generate import FIELD_ID, LOT_IDS, LOT_NAMES

pytestmark = pytest.mark.slow

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
async def csv_lots(session):
    """Creates the field + 10 lots referenced by tests/fixtures/animals.csv."""
    async with session.begin():
        await session.execute(
            text("INSERT INTO fields (id, name) VALUES (:id, 'CSV Scale Field')"),
            {"id": FIELD_ID},
        )
        for lot_id, lot_name in zip(LOT_IDS, LOT_NAMES):
            await session.execute(
                text("INSERT INTO lots (id, name, field_id) VALUES (:id, :name, :fid)"),
                {"id": lot_id, "name": lot_name, "fid": FIELD_ID},
            )


async def test_bulk_create_1200_animals_via_csv(client, csv_lots):
    resp = await client.post(
        "/animals/bulk",
        files={"file": ("animals.csv", (FIXTURES / "animals.csv").read_bytes(), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 50_000
    assert data["failed"] == []


async def test_bulk_weight_events_via_csv(client, csv_lots):
    await client.post(
        "/animals/bulk",
        files={"file": ("animals.csv", (FIXTURES / "animals.csv").read_bytes(), "text/csv")},
    )

    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "WEIGHT"},
        files={"file": ("events_weight.csv", (FIXTURES / "events_weight.csv").read_bytes(), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 200_000  # 50_000 animals × 4 measurements
    assert data["failed"] == []


async def test_bulk_vaccination_events_via_csv(client, csv_lots):
    await client.post(
        "/animals/bulk",
        files={"file": ("animals.csv", (FIXTURES / "animals.csv").read_bytes(), "text/csv")},
    )

    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "VACCINATION"},
        files={"file": ("events_vaccination.csv", (FIXTURES / "events_vaccination.csv").read_bytes(), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 50_000
    assert data["failed"] == []


async def test_get_animals_pagination_after_bulk_load(client, csv_lots):
    await client.post(
        "/animals/bulk",
        files={"file": ("animals.csv", (FIXTURES / "animals.csv").read_bytes(), "text/csv")},
    )

    resp = await client.get("/animals", params={"page": 1, "limit": 100})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 100
    assert body["has_next"] is True

    # Last page: 50_000 animals / 100 per page = page 500 is last
    resp = await client.get("/animals", params={"page": 500, "limit": 100})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 100
    assert body["has_next"] is False
