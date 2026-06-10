import uuid
from datetime import datetime

from sqlalchemy import bindparam, text, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from app.models.animal_lot_period import AnimalLotPeriod
from app.repositories.base import BaseRepository


class AnimalLotPeriodRepository(BaseRepository[AnimalLotPeriod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AnimalLotPeriod, session)

    async def bulk_close_active(
        self, animal_ids: list[uuid.UUID], exited_ats: list[datetime]
    ) -> None:
        stmt = text("""
            UPDATE animal_lot_periods AS alp
            SET exited_at = t.exited_at
            FROM (
                SELECT
                    CAST(UNNEST(:animal_ids) AS uuid) AS animal_id,
                    CAST(UNNEST(:exited_ats) AS timestamptz) AS exited_at
            ) t
            WHERE alp.animal_id = t.animal_id
              AND alp.exited_at IS NULL
        """).bindparams(
            bindparam("animal_ids", type_=ARRAY(String())),
            bindparam("exited_ats", type_=ARRAY(String())),
        )
        await self.session.execute(stmt, {
            "animal_ids": [str(aid) for aid in animal_ids],
            "exited_ats": [e.isoformat() for e in exited_ats],
        })

    async def bulk_open(
        self,
        animal_ids: list[uuid.UUID],
        lot_ids: list[uuid.UUID],
        entered_ats: list[datetime],
    ) -> None:
        stmt = text("""
            INSERT INTO animal_lot_periods (animal_id, lot_id, entered_at)
            SELECT
                CAST(UNNEST(:animal_ids) AS uuid),
                CAST(UNNEST(:lot_ids) AS uuid),
                CAST(UNNEST(:entered_ats) AS timestamptz)
        """).bindparams(
            bindparam("animal_ids", type_=ARRAY(String())),
            bindparam("lot_ids", type_=ARRAY(String())),
            bindparam("entered_ats", type_=ARRAY(String())),
        )
        await self.session.execute(stmt, {
            "animal_ids": [str(aid) for aid in animal_ids],
            "lot_ids": [str(lid) for lid in lot_ids],
            "entered_ats": [e.isoformat() for e in entered_ats],
        })

    async def bulk_create_initial(
        self,
        animal_ids: list[uuid.UUID],
        lot_ids: list[uuid.UUID],
        entered_ats: list[datetime],
    ) -> None:
        await self.bulk_open(animal_ids, lot_ids, entered_ats)
