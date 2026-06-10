import uuid

from sqlalchemy import text


def _animal(lot_id: uuid.UUID, tag: str) -> dict:
    return {
        "tag_number": tag,
        "breed": "ANGUS",
        "category": "COW",
        "birth_date": "2020-01-01",
        "lot_id": str(lot_id),
        "occurred_at": "2025-01-01T00:00:00Z",
    }


async def _create_animal(client, session, lot_id: uuid.UUID, tag: str) -> uuid.UUID:
    await client.post("/animals/bulk", json={"animals": [_animal(lot_id, tag)]})
    r = await session.execute(
        text("SELECT id FROM animals WHERE tag_number = :tag"),
        {"tag": tag},
    )
    animal_id = r.scalar_one()
    await session.commit()
    return animal_id


async def test_get_lot_animals(client, session, lot):
    await _create_animal(client, session, lot, "LA-001")
    await _create_animal(client, session, lot, "LA-002")

    resp = await client.get(f"/lots/{lot}/animals")
    assert resp.status_code == 200
    animals = resp.json()["animals"]
    tags = [a["tag_number"] for a in animals]
    assert "LA-001" in tags
    assert "LA-002" in tags


async def test_get_lot_animals_empty(client, lot):
    resp = await client.get(f"/lots/{lot}/animals")
    assert resp.status_code == 200
    assert resp.json()["animals"] == []


async def test_get_lot_adg(client, session, lot):
    animal_id = await _create_animal(client, session, lot, "ADG-001")

    # Two weight events 31 days apart: 200 kg → 231 kg → ADG = 1.0 kg/day
    for occurred_at, weight in [
        ("2026-01-10T00:00:00Z", "200"),
        ("2026-02-10T00:00:00Z", "231"),
    ]:
        await client.post(
            "/animals/bulk/events",
            params={"type": "WEIGHT"},
            json={"events": [{"animal_id": str(animal_id), "occurred_at": occurred_at, "payload": {"weight_kg": weight}}]},
        )

    resp = await client.get(
        f"/lots/{lot}/adg",
        params={"from": "2026-01-01T00:00:00Z", "to": "2026-03-01T00:00:00Z", "min_days": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["animals_count"] == 1
    assert abs(float(data["avg_adg_kg_day"]) - 1.0) < 0.01


async def test_get_lot_adg_no_animals(client, lot):
    resp = await client.get(
        f"/lots/{lot}/adg",
        params={"from": "2026-01-01T00:00:00Z", "to": "2026-03-01T00:00:00Z", "min_days": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["animals_count"] == 0
    assert data["avg_adg_kg_day"] is None


async def test_get_lot_adg_min_days_filter(client, session, lot):
    animal_id = await _create_animal(client, session, lot, "ADG-002")

    # Two weight events only 5 days apart — min_days=10 should exclude them
    for occurred_at, weight in [
        ("2026-01-10T00:00:00Z", "200"),
        ("2026-01-15T00:00:00Z", "210"),
    ]:
        await client.post(
            "/animals/bulk/events",
            params={"type": "WEIGHT"},
            json={"events": [{"animal_id": str(animal_id), "occurred_at": occurred_at, "payload": {"weight_kg": weight}}]},
        )

    resp = await client.get(
        f"/lots/{lot}/adg",
        params={"from": "2026-01-01T00:00:00Z", "to": "2026-03-01T00:00:00Z", "min_days": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["animals_count"] == 0
