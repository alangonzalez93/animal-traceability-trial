import uuid

from sqlalchemy import text


def _animal(lot_id: uuid.UUID, tag: str = "TAG-001") -> dict:
    return {
        "tag_number": tag,
        "breed": "ANGUS",
        "category": "CALF",
        "birth_date": "2022-01-01",
        "lot_id": str(lot_id),
        "occurred_at": "2025-01-01T00:00:00Z",
    }


async def test_bulk_create_json(client, lot):
    resp = await client.post(
        "/animals/bulk",
        json={"animals": [_animal(lot, "TAG-A"), _animal(lot, "TAG-B")]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["failed"] == []


async def test_bulk_create_unknown_lot_reported_as_failed(client):
    resp = await client.post(
        "/animals/bulk",
        json={"animals": [_animal(uuid.uuid4(), "TAG-NOLOT")]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0
    assert len(data["failed"]) == 1


async def test_bulk_create_csv(client, lot):
    csv_content = (
        "tag_number,breed,category,birth_date,lot_id,occurred_at\n"
        f"TAG-CSV,ANGUS,CALF,2022-01-01,{lot},2026-01-01T00:00:00Z\n"
    )
    resp = await client.post(
        "/animals/bulk",
        files={"file": ("animals.csv", csv_content.encode(), "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1


async def test_get_history_returns_birth_event(client, session, lot):
    await client.post("/animals/bulk", json={"animals": [_animal(lot, "TAG-HIST")]})

    r = await session.execute(
        text("SELECT id FROM animals WHERE tag_number = 'TAG-HIST'")
    )
    animal_id = r.scalar_one()
    await session.commit()

    resp = await client.get(f"/animals/{animal_id}/history")
    assert resp.status_code == 200
    events = resp.json()["data"]
    assert len(events) >= 1
    types = [e["type"] for e in events]
    assert "BIRTH" in types


async def test_get_history_pagination(client, session, lot):
    await client.post("/animals/bulk", json={"animals": [_animal(lot, "TAG-PAGE")]})
    r = await session.execute(
        text("SELECT id FROM animals WHERE tag_number = 'TAG-PAGE'")
    )
    animal_id = r.scalar_one()
    await session.commit()

    resp = await client.get(f"/animals/{animal_id}/history", params={"page": 1, "limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["limit"] == 10
    assert isinstance(body["has_next"], bool)


async def test_get_history_not_found(client):
    resp = await client.get(f"/animals/{uuid.uuid4()}/history")
    assert resp.status_code == 404
