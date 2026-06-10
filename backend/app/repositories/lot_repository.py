import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.animal import Animal
from app.models.enums import AnimalStatus
from app.models.lot import Lot
from app.repositories.base import BaseRepository


class LotRepository(BaseRepository[Lot]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Lot, session)

    async def get_by_id(self, id: uuid.UUID) -> Lot | None:
        result = await self.session.execute(
            select(Lot).where(Lot.id == id, Lot.deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def get_paginated(
        self,
        page: int,
        limit: int,
        field_id: uuid.UUID | None = None,
    ) -> list[Lot]:
        offset = (page - 1) * limit
        stmt = (
            select(Lot)
            .where(Lot.deleted == False)  # noqa: E712
            .order_by(Lot.name)
            .offset(offset)
            .limit(limit + 1)
        )
        if field_id is not None:
            stmt = stmt.where(Lot.field_id == field_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ids(self, ids: list[uuid.UUID]) -> list[Lot]:
        result = await self.session.execute(
            select(Lot).where(Lot.id.in_(ids), Lot.deleted == False)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_animals_by_lot(self, lot_id: uuid.UUID) -> list[Animal]:
        result = await self.session.execute(
            select(Animal).where(
                Animal.current_lot_id == lot_id,
                Animal.status == AnimalStatus.ACTIVE,
                Animal.deleted == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())
