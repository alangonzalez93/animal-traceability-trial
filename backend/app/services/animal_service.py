import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.animal_lot_period_repository import AnimalLotPeriodRepository
from app.repositories.animal_repository import AnimalRepository
from app.repositories.event_repository import EventRepository
from app.repositories.lot_repository import LotRepository
from app.models.animal import Animal
from app.models.enums import Breed, AnimalCategory, AnimalStatus, EventType

logger = logging.getLogger(__name__)


class AnimalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.animal_repo = AnimalRepository(session)
        self.event_repo = EventRepository(session)
        self.lot_repo = LotRepository(session)
        self.period_repo = AnimalLotPeriodRepository(session)

    async def get_animal(self, animal_id: uuid.UUID) -> Animal:
        animal = await self.animal_repo.get_by_id(animal_id)
        if animal is None or animal.deleted:
            raise HTTPException(status_code=404, detail="Animal not found")
        return animal

    async def get_animals(
        self,
        page: int,
        limit: int,
        status: AnimalStatus | None = None,
        lot_id: uuid.UUID | None = None,
        tag_number: str | None = None,
    ) -> dict:
        animals = await self.animal_repo.get_paginated(page, limit, status=status, lot_id=lot_id, tag_number=tag_number)
        has_next = len(animals) > limit
        return {
            "data": animals[:limit],
            "page": page,
            "limit": limit,
            "has_next": has_next,
        }

    async def bulk_create_animals(
        self,
        rows: list[dict],
    ) -> dict:
        failed: list[dict] = []
        created = 0

        async with self.session.begin():
            # Validate all unique lot_ids in a single query
            unique_lot_ids = list(dict.fromkeys(row["lot_id"] for row in rows))
            existing_lots = await self.lot_repo.get_by_ids(unique_lot_ids)
            valid_lot_ids = {lot.id for lot in existing_lots}

            valid: list[dict] = []
            for i, row in enumerate(rows):
                lot_id = row["lot_id"] if isinstance(row["lot_id"], uuid.UUID) else uuid.UUID(str(row["lot_id"]))
                if lot_id not in valid_lot_ids:
                    failed.append({"row": i + 1, "reason": f"lot_id {row['lot_id']} not found"})
                else:
                    valid.append(row)

            if valid:
                occurred_ats = [
                    row.get("occurred_at") or datetime.now(timezone.utc) for row in valid
                ]

                animal_ids = await self.animal_repo.bulk_create(
                    tag_numbers=[r["tag_number"] for r in valid],
                    breeds=[r["breed"] for r in valid],
                    categories=[r["category"] for r in valid],
                    birth_dates=[r["birth_date"] for r in valid],
                    lot_ids=[r["lot_id"] for r in valid],
                )

                await self.event_repo.bulk_create(
                    animal_ids=animal_ids,
                    event_type=EventType.BIRTH,
                    occurred_ats=occurred_ats,
                    payloads=[{} for _ in valid],
                )

                await self.period_repo.bulk_create_initial(
                    animal_ids=animal_ids,
                    lot_ids=[r["lot_id"] for r in valid],
                    entered_ats=occurred_ats,
                )

                created = len(animal_ids)

        return {"created": created, "failed": failed}
