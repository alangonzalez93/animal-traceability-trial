import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lot import Lot
from app.repositories.event_repository import EventRepository
from app.repositories.lot_repository import LotRepository

logger = logging.getLogger(__name__)


class LotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.lot_repo = LotRepository(session)
        self.event_repo = EventRepository(session)

    async def get_lot(self, lot_id: uuid.UUID) -> Lot:
        lot = await self.lot_repo.get_by_id(lot_id)
        if lot is None:
            raise HTTPException(status_code=404, detail="Lot not found")
        return lot

    async def get_lots(
        self,
        page: int,
        limit: int,
        field_id: uuid.UUID | None = None,
    ) -> dict:
        lots = await self.lot_repo.get_paginated(page, limit, field_id=field_id)
        has_next = len(lots) > limit
        return {
            "data": lots[:limit],
            "page": page,
            "limit": limit,
            "has_next": has_next,
        }

    async def get_lot_animals(self, lot_id: uuid.UUID) -> list:
        lot = await self.lot_repo.get_by_id(lot_id)
        if lot is None:
            raise HTTPException(status_code=404, detail="Lot not found")
        return await self.lot_repo.get_animals_by_lot(lot_id)

    async def get_lot_adg(
        self,
        lot_id: uuid.UUID,
        from_date: datetime,
        to_date: datetime,
        min_days: int,
    ) -> dict:
        lot = await self.lot_repo.get_by_id(lot_id)
        if lot is None:
            raise HTTPException(status_code=404, detail="Lot not found")
        adg = await self.event_repo.get_adg(lot_id, from_date, to_date, min_days)
        return {
            "lot_id": lot_id,
            "lot_name": lot.name,
            "period": {"from": from_date, "to": to_date},
            "animals_count": adg["animals_count"],
            "avg_adg_kg_day": adg["avg_adg_kg_day"],
        }
