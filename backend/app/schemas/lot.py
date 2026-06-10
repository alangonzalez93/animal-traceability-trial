import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class LotResponse(BaseModel):
    id: uuid.UUID
    name: str
    field_id: uuid.UUID

    model_config = {"from_attributes": True}


class LotAnimalsResponse(BaseModel):
    animals: list[dict]


class AdgResponse(BaseModel):
    lot_id: uuid.UUID
    lot_name: str
    period: dict
    animals_count: int
    avg_adg_kg_day: Decimal | None
