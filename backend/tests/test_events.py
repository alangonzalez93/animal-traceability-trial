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
    # Commit the autobegun read transaction so service's session.begin() can start fresh.
    await session.commit()
    return animal_id


async def test_bulk_weight_event(client, session, lot):
    animal_id = await _create_animal(client, session, lot, "W-001")

    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "WEIGHT"},
        json={"events": [
            {
                "animal_id": str(animal_id),
                "occurred_at": "2026-02-01T00:00:00Z",
                "payload": {"weight_kg": "250.5"},
            }
        ]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 1
    assert data["failed"] == []


async def test_bulk_vaccination_event(client, session, lot):
    animal_id = await _create_animal(client, session, lot, "V-001")

    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "VACCINATION"},
        json={"events": [
            {
                "animal_id": str(animal_id),
                "occurred_at": "2026-02-01T00:00:00Z",
                "payload": {"vaccine_name": "FMD"},
            }
        ]},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1


async def test_bulk_move_event_via_json_payload(client, session, lot_pair):
    lot_a, lot_b = lot_pair
    animal_id = await _create_animal(client, session, lot_a, "M-001")

    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "MOVE"},
        json={"events": [
            {
                "animal_id": str(animal_id),
                "occurred_at": "2026-03-01T00:00:00Z",
                "payload": {"from_lot_id": str(lot_a), "to_lot_id": str(lot_b)},
            }
        ]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 1
    assert data["failed"] == []

    # Animal's current_lot_id should now be lot_b
    r = await session.execute(
        text("SELECT current_lot_id FROM animals WHERE id = :aid"),
        {"aid": str(animal_id)},
    )
    assert r.scalar_one() == lot_b


async def test_bulk_move_wrong_from_lot_reported_as_failed(client, session, lot_pair):
    lot_a, lot_b = lot_pair
    animal_id = await _create_animal(client, session, lot_a, "M-002")

    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "MOVE"},
        json={"events": [
            {
                "animal_id": str(animal_id),
                "occurred_at": "2026-03-01T00:00:00Z",
                # from_lot_id is lot_b but animal is in lot_a → should fail
                "payload": {"from_lot_id": str(lot_b), "to_lot_id": str(lot_a)},
            }
        ]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0
    assert len(data["failed"]) == 1


async def test_bulk_event_unknown_animal_reported_as_failed(client, lot):
    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "WEIGHT"},
        json={"events": [
            {
                "animal_id": str(uuid.uuid4()),
                "occurred_at": "2026-02-01T00:00:00Z",
                "payload": {"weight_kg": "200"},
            }
        ]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0
    assert len(data["failed"]) == 1


async def test_bulk_death_event_marks_animal_dead(client, session, lot):
    animal_id = await _create_animal(client, session, lot, "D-001")

    resp = await client.post(
        "/animals/bulk/events",
        params={"type": "DEATH"},
        json={"events": [
            {
                "animal_id": str(animal_id),
                "occurred_at": "2026-06-01T00:00:00Z",
                "payload": {},
            }
        ]},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 1

    r = await session.execute(
        text("SELECT status FROM animals WHERE id = :aid"),
        {"aid": str(animal_id)},
    )
    assert r.scalar_one() == "DEAD"
