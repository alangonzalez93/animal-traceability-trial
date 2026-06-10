import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AnimalStatus, AnimalCategory, EventType
from app.repositories.animal_lot_period_repository import AnimalLotPeriodRepository
from app.repositories.animal_repository import AnimalRepository
from app.repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.animal_repo = AnimalRepository(session)
        self.event_repo = EventRepository(session)
        self.period_repo = AnimalLotPeriodRepository(session)

    async def get_animal_history(
        self, animal_id: uuid.UUID, page: int, limit: int
    ) -> dict:
        animal = await self.animal_repo.get_by_id(animal_id)
        if animal is None or animal.deleted:
            raise HTTPException(status_code=404, detail="Animal not found")

        events = await self.event_repo.get_history(animal_id, page, limit)
        has_next = len(events) > limit
        return {
            "data": events[:limit],
            "page": page,
            "limit": limit,
            "has_next": has_next,
        }

    async def _resolve_tag_numbers(self, rows: list[dict]) -> tuple[list[dict], list[dict]]:
        tag_numbers = [r["tag_number"] for r in rows]
        animals = await self.animal_repo.get_by_tag_numbers(tag_numbers)
        by_tag = {a.tag_number: a.id for a in animals}

        resolved, failed = [], []
        for i, r in enumerate(rows):
            animal_id = by_tag.get(r["tag_number"])
            if animal_id is None:
                failed.append({"row": i + 1, "reason": f"tag_number {r['tag_number']} not found"})
            else:
                resolved.append({**r, "animal_id": animal_id})
        return resolved, failed

    async def bulk_create_events(self, event_type: EventType, rows: list[dict]) -> dict:
        async with self.session.begin():
            # CSV rows carry tag_number; JSON rows carry animal_id directly
            pre_failed: list[dict] = []
            if rows and "tag_number" in rows[0]:
                rows, pre_failed = await self._resolve_tag_numbers(rows)
                if not rows:
                    return {"created": 0, "failed": pre_failed}

            if event_type == EventType.MOVE:
                result = await self._handle_move(rows)
            elif event_type in (EventType.DEATH, EventType.SALE):
                result = await self._handle_status_change(event_type, rows)
            elif event_type == EventType.RECLASSIFICATION:
                result = await self._handle_reclassification(rows)
            else:
                result = await self._handle_simple(event_type, rows)

        result["failed"] = pre_failed + result["failed"]
        return result

    async def _handle_move(self, rows: list[dict]) -> dict:
        valid: list[dict] = []
        failed: list[dict] = []

        animal_ids = [r["animal_id"] for r in rows]

        # SELECT FOR UPDATE with consistent lock order to prevent deadlocks
        locked = await self.animal_repo.lock_for_update(animal_ids)
        locked_by_id = {a.id: a for a in locked}

        for i, row in enumerate(rows):
            # from_lot_id / to_lot_id come from top-level keys (CSV path) or payload (JSON path)
            pl = row.get("payload") or {}
            from_lot_id = row.get("from_lot_id") or pl.get("from_lot_id")
            to_lot_id = row.get("to_lot_id") or pl.get("to_lot_id")
            if not from_lot_id or not to_lot_id:
                failed.append({"row": i + 1, "reason": "from_lot_id and to_lot_id required"})
                continue

            animal = locked_by_id.get(row["animal_id"])
            if animal is None:
                failed.append({"row": i + 1, "reason": "animal not found"})
                continue
            if str(animal.current_lot_id) != str(from_lot_id):
                failed.append({"row": i + 1, "reason": "animal not in from_lot_id"})
                continue
            valid.append({
                **row,
                "from_lot_id": uuid.UUID(str(from_lot_id)),
                "to_lot_id": uuid.UUID(str(to_lot_id)),
            })

        if not valid:
            return {"created": 0, "failed": failed}

        valid_ids = [r["animal_id"] for r in valid]
        occurred_ats = [r["occurred_at"] for r in valid]
        to_lot_ids = [r["to_lot_id"] for r in valid]
        payloads = [{"from_lot_id": str(r["from_lot_id"]), "to_lot_id": str(r["to_lot_id"])} for r in valid]

        await self.event_repo.bulk_create(valid_ids, EventType.MOVE, occurred_ats, payloads)
        await self.animal_repo.bulk_update_current_lots(valid_ids, to_lot_ids)
        await self.period_repo.bulk_close_active(valid_ids, occurred_ats)
        await self.period_repo.bulk_open(valid_ids, to_lot_ids, occurred_ats)

        return {"created": len(valid), "failed": failed}

    async def _handle_status_change(self, event_type: EventType, rows: list[dict]) -> dict:
        valid: list[dict] = []
        failed: list[dict] = []

        animal_ids = [r["animal_id"] for r in rows]
        animals_by_id = {a.id: a for a in await self.animal_repo.get_by_ids(animal_ids)}

        for i, row in enumerate(rows):
            animal = animals_by_id.get(row["animal_id"])
            if animal is None or animal.deleted:
                failed.append({"row": i + 1, "reason": "animal not found"})
                continue
            valid.append(row)

        if not valid:
            return {"created": 0, "failed": failed}

        valid_ids = [r["animal_id"] for r in valid]
        occurred_ats = [r["occurred_at"] for r in valid]
        new_status = AnimalStatus.DEAD if event_type == EventType.DEATH else AnimalStatus.SOLD

        await self.event_repo.bulk_create(valid_ids, event_type, occurred_ats, [{} for _ in valid])
        await self.animal_repo.bulk_update(valid_ids, status=new_status)

        return {"created": len(valid), "failed": failed}

    async def _handle_reclassification(self, rows: list[dict]) -> dict:
        valid: list[dict] = []
        failed: list[dict] = []

        animal_ids = [r["animal_id"] for r in rows]
        animals_by_id = {a.id: a for a in await self.animal_repo.get_by_ids(animal_ids)}

        for i, row in enumerate(rows):
            animal = animals_by_id.get(row["animal_id"])
            if animal is None or animal.deleted:
                failed.append({"row": i + 1, "reason": "animal not found"})
                continue
            valid.append(row)

        if not valid:
            return {"created": 0, "failed": failed}

        valid_ids = [r["animal_id"] for r in valid]
        occurred_ats = [r["occurred_at"] for r in valid]
        payloads = [{"new_category": r["new_category"].value} for r in valid]
        categories = [r["new_category"] for r in valid]

        await self.event_repo.bulk_create(valid_ids, EventType.RECLASSIFICATION, occurred_ats, payloads)
        await self.animal_repo.bulk_update_categories(valid_ids, categories)

        return {"created": len(valid), "failed": failed}

    async def _handle_simple(self, event_type: EventType, rows: list[dict]) -> dict:
        valid: list[dict] = []
        failed: list[dict] = []

        animal_ids = [r["animal_id"] for r in rows]
        animals_by_id = {a.id: a for a in await self.animal_repo.get_by_ids(animal_ids)}

        for i, row in enumerate(rows):
            animal = animals_by_id.get(row["animal_id"])
            if animal is None or animal.deleted:
                failed.append({"row": i + 1, "reason": "animal not found"})
                continue
            valid.append(row)

        if not valid:
            return {"created": 0, "failed": failed}

        valid_ids = [r["animal_id"] for r in valid]
        occurred_ats = [r["occurred_at"] for r in valid]
        payloads = [r.get("payload", {}) for r in valid]

        await self.event_repo.bulk_create(valid_ids, event_type, occurred_ats, payloads)
        return {"created": len(valid), "failed": failed}
