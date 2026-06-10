import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import AnimalCategory, AnimalStatus, Breed


class AnimalBulkCreateItem(BaseModel):
    tag_number: str
    breed: Breed
    category: AnimalCategory
    birth_date: date
    lot_id: uuid.UUID
    occurred_at: datetime | None = None


class AnimalBulkCreateRequest(BaseModel):
    animals: list[AnimalBulkCreateItem]


class AnimalBulkCreateResponse(BaseModel):
    created: int
    failed: list[dict]


class AnimalResponse(BaseModel):
    id: uuid.UUID
    tag_number: str
    breed: Breed
    category: AnimalCategory
    status: AnimalStatus
    birth_date: date
    current_lot_id: uuid.UUID | None

    model_config = {"from_attributes": True}
