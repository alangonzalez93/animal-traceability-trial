import uuid
from datetime import date
from typing import Any

from sqlalchemy import bindparam, select, text, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from app.models.animal import Animal
from app.models.enums import AnimalCategory, AnimalStatus, Breed
from app.repositories.base import BaseRepository


class AnimalRepository(BaseRepository[Animal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Animal, session)

    async def bulk_create(
        self,
        tag_numbers: list[str],
        breeds: list[Breed],
        categories: list[AnimalCategory],
        birth_dates: list[date],
        lot_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        stmt = text("""
            INSERT INTO animals (tag_number, breed, category, status, birth_date, current_lot_id)
            SELECT
                UNNEST(:tag_numbers),
                CAST(UNNEST(:breeds) AS breed),
                CAST(UNNEST(:categories) AS animal_category),
                CAST('ACTIVE' AS animal_status),
                CAST(UNNEST(:birth_dates) AS date),
                CAST(UNNEST(:lot_ids) AS uuid)
            RETURNING id
        """).bindparams(
            bindparam("tag_numbers", type_=ARRAY(String())),
            bindparam("breeds", type_=ARRAY(String())),
            bindparam("categories", type_=ARRAY(String())),
            bindparam("birth_dates", type_=ARRAY(String())),
            bindparam("lot_ids", type_=ARRAY(String())),
        )
        result = await self.session.execute(stmt, {
            "tag_numbers": tag_numbers,
            "breeds": [b.value for b in breeds],
            "categories": [c.value for c in categories],
            "birth_dates": [str(d) for d in birth_dates],
            "lot_ids": [str(lid) for lid in lot_ids],
        })
        return [row[0] for row in result.fetchall()]

    async def get_paginated(
        self,
        page: int,
        limit: int,
        status: AnimalStatus | None = None,
        lot_id: uuid.UUID | None = None,
        tag_number: str | None = None,
    ) -> list[Animal]:
        offset = (page - 1) * limit
        stmt = (
            select(Animal)
            .where(Animal.deleted == False)  # noqa: E712
            .order_by(Animal.created_at.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        if status is not None:
            stmt = stmt.where(Animal.status == status)
        if lot_id is not None:
            stmt = stmt.where(Animal.current_lot_id == lot_id)
        if tag_number is not None:
            stmt = stmt.where(Animal.tag_number == tag_number)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tag_numbers(self, tag_numbers: list[str]) -> list[Animal]:
        result = await self.session.execute(
            select(Animal).where(Animal.tag_number.in_(tag_numbers))
        )
        return list(result.scalars().all())

    async def get_by_ids(self, ids: list[uuid.UUID]) -> list[Animal]:
        result = await self.session.execute(
            select(Animal).where(Animal.id.in_(ids))
        )
        return list(result.scalars().all())

    async def bulk_update(self, animal_ids: list[uuid.UUID], **fields: Any) -> None:
        await self.session.execute(
            update(Animal).where(Animal.id.in_(animal_ids)).values(**fields)
        )

    async def bulk_update_current_lots(
        self, animal_ids: list[uuid.UUID], lot_ids: list[uuid.UUID]
    ) -> None:
        stmt = text("""
            UPDATE animals AS a
            SET current_lot_id = t.lot_id
            FROM (
                SELECT
                    CAST(UNNEST(:animal_ids) AS uuid) AS animal_id,
                    CAST(UNNEST(:lot_ids) AS uuid) AS lot_id
            ) t
            WHERE a.id = t.animal_id
        """).bindparams(
            bindparam("animal_ids", type_=ARRAY(String())),
            bindparam("lot_ids", type_=ARRAY(String())),
        )
        await self.session.execute(stmt, {
            "animal_ids": [str(aid) for aid in animal_ids],
            "lot_ids": [str(lid) for lid in lot_ids],
        })

    async def bulk_update_categories(
        self, animal_ids: list[uuid.UUID], categories: list[AnimalCategory]
    ) -> None:
        stmt = text("""
            UPDATE animals AS a
            SET category = CAST(t.category AS animal_category)
            FROM (
                SELECT
                    CAST(UNNEST(:animal_ids) AS uuid) AS animal_id,
                    UNNEST(:categories) AS category
            ) t
            WHERE a.id = t.animal_id
        """).bindparams(
            bindparam("animal_ids", type_=ARRAY(String())),
            bindparam("categories", type_=ARRAY(String())),
        )
        await self.session.execute(stmt, {
            "animal_ids": [str(aid) for aid in animal_ids],
            "categories": [c.value for c in categories],
        })

    async def lock_for_update(self, animal_ids: list[uuid.UUID]) -> list[Animal]:
        result = await self.session.execute(
            select(Animal)
            .where(Animal.id.in_(animal_ids))
            .order_by(Animal.id)  # consistent acquisition order prevents deadlocks
            .with_for_update()
        )
        return list(result.scalars().all())
