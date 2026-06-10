import json
import uuid
from datetime import datetime

from sqlalchemy import bindparam, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String

from app.models.enums import EventType
from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Event, session)

    async def bulk_create(
        self,
        animal_ids: list[uuid.UUID],
        event_type: EventType,
        occurred_ats: list[datetime],
        payloads: list[dict],
    ) -> list[uuid.UUID]:
        stmt = text("""
            INSERT INTO events (animal_id, type, occurred_at, payload)
            SELECT
                CAST(UNNEST(:animal_ids) AS uuid),
                CAST(:event_type AS event_type),
                CAST(UNNEST(:occurred_ats) AS timestamptz),
                CAST(UNNEST(:payloads) AS jsonb)
            RETURNING id
        """).bindparams(
            bindparam("animal_ids", type_=ARRAY(String())),
            bindparam("occurred_ats", type_=ARRAY(String())),
            bindparam("payloads", type_=ARRAY(String())),
        )
        result = await self.session.execute(stmt, {
            "animal_ids": [str(aid) for aid in animal_ids],
            "event_type": event_type.value,
            "occurred_ats": [o.isoformat() for o in occurred_ats],
            "payloads": [json.dumps(p) for p in payloads],
        })
        return [row[0] for row in result.fetchall()]

    async def get_history(
        self, animal_id: uuid.UUID, page: int, limit: int
    ) -> list[Event]:
        offset = (page - 1) * limit
        result = await self.session.execute(
            select(Event)
            .where(Event.animal_id == animal_id)
            .order_by(Event.occurred_at.desc())
            .offset(offset)
            .limit(limit + 1)
        )
        return list(result.scalars().all())

    async def get_adg(
        self,
        lot_id: uuid.UUID,
        from_date: datetime,
        to_date: datetime,
        min_days: int,
    ) -> dict:
        # CAST() is used instead of :: to avoid asyncpg named-parameter parsing issues.
        # from_date / to_date are passed as Python datetime objects — asyncpg infers
        # the type as timestamptz from the CAST hint and rejects ISO strings.
        result = await self.session.execute(
            text("""
                WITH lot_periods AS (
                    SELECT animal_id
                    FROM animal_lot_periods
                    WHERE lot_id = CAST(:lot_id AS uuid)
                      AND entered_at < CAST(:to_date AS timestamptz)
                      AND (exited_at IS NULL OR exited_at > CAST(:from_date AS timestamptz))
                ),
                first_weight AS (
                    SELECT DISTINCT ON (e.animal_id)
                        e.animal_id,
                        CAST(e.payload->>'weight_kg' AS numeric) AS weight_kg,
                        e.occurred_at
                    FROM events e
                    JOIN lot_periods lp ON lp.animal_id = e.animal_id
                    WHERE e.type = 'WEIGHT'
                      AND e.occurred_at >= CAST(:from_date AS timestamptz)
                      AND e.occurred_at < CAST(:to_date AS timestamptz)
                    ORDER BY e.animal_id, e.occurred_at ASC
                ),
                last_weight AS (
                    SELECT DISTINCT ON (e.animal_id)
                        e.animal_id,
                        CAST(e.payload->>'weight_kg' AS numeric) AS weight_kg,
                        e.occurred_at
                    FROM events e
                    JOIN lot_periods lp ON lp.animal_id = e.animal_id
                    WHERE e.type = 'WEIGHT'
                      AND e.occurred_at >= CAST(:from_date AS timestamptz)
                      AND e.occurred_at < CAST(:to_date AS timestamptz)
                    ORDER BY e.animal_id, e.occurred_at DESC
                ),
                adg_per_animal AS (
                    SELECT
                        fw.animal_id,
                        (lw.weight_kg - fw.weight_kg) /
                            NULLIF(EXTRACT(EPOCH FROM (lw.occurred_at - fw.occurred_at)) / 86400, 0)
                            AS adg
                    FROM first_weight fw
                    JOIN last_weight lw ON lw.animal_id = fw.animal_id
                    WHERE EXTRACT(EPOCH FROM (lw.occurred_at - fw.occurred_at)) / 86400 >= :min_days
                      AND lw.occurred_at > fw.occurred_at
                )
                SELECT
                    CAST(COUNT(*) AS integer) AS animals_count,
                    AVG(adg)                  AS avg_adg_kg_day
                FROM adg_per_animal
            """),
            {
                "lot_id": str(lot_id),
                "from_date": from_date,
                "to_date": to_date,
                "min_days": min_days,
            },
        )
        row = result.mappings().one()
        return dict(row)
