import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import EventType


class EventBulkCreateItem(BaseModel):
    animal_id: uuid.UUID
    occurred_at: datetime
    payload: dict = {}


class EventBulkCreateRequest(BaseModel):
    events: list[EventBulkCreateItem]


class EventBulkCreateResponse(BaseModel):
    created: int
    failed: list[dict]


class EventResponse(BaseModel):
    id: uuid.UUID
    animal_id: uuid.UUID
    type: EventType
    occurred_at: datetime
    payload: dict

    model_config = {"from_attributes": True}
