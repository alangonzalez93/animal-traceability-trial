import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.enums import AnimalCategory, AnimalStatus, Breed, EventType
from app.schemas.animal import AnimalBulkCreateRequest, AnimalBulkCreateResponse, AnimalResponse
from app.schemas.common import PaginatedResponse
from app.schemas.event import EventBulkCreateRequest, EventBulkCreateResponse, EventResponse
from app.services.animal_service import AnimalService
from app.services.event_service import EventService

router = APIRouter(prefix="/animals", tags=["animals"])

# CSV column mapping per event type
_CSV_EVENT_COLUMNS: dict[EventType, list[str]] = {
    EventType.WEIGHT: ["tag_number", "occurred_at", "weight_kg"],
    EventType.MOVE: ["tag_number", "occurred_at", "from_lot_id", "to_lot_id"],
    EventType.DEATH: ["tag_number", "occurred_at"],
    EventType.SALE: ["tag_number", "occurred_at"],
    EventType.VACCINATION: ["tag_number", "occurred_at", "vaccine_name"],
    EventType.RECLASSIFICATION: ["tag_number", "occurred_at", "new_category"],
    EventType.BIRTH: ["tag_number", "occurred_at"],
}

_BATCH_SIZE = 1000


def _parse_csv_event_row(row: dict, event_type: EventType) -> dict:
    parsed: dict = {
        "tag_number": row["tag_number"],
        "occurred_at": datetime.fromisoformat(row["occurred_at"]),
    }
    if event_type == EventType.WEIGHT:
        from decimal import Decimal
        parsed["payload"] = {"weight_kg": str(Decimal(row["weight_kg"]))}
    elif event_type == EventType.MOVE:
        parsed["from_lot_id"] = uuid.UUID(row["from_lot_id"])
        parsed["to_lot_id"] = uuid.UUID(row["to_lot_id"])
    elif event_type == EventType.VACCINATION:
        parsed["payload"] = {"vaccine_name": row["vaccine_name"]}
    elif event_type == EventType.RECLASSIFICATION:
        parsed["new_category"] = AnimalCategory(row["new_category"])
        parsed["payload"] = {"new_category": row["new_category"]}
    return parsed


@router.get("/{animal_id}", response_model=AnimalResponse)
async def get_animal(
    animal_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> AnimalResponse:
    service = AnimalService(session)
    animal = await service.get_animal(animal_id)
    return AnimalResponse.model_validate(animal)


@router.get("", response_model=PaginatedResponse[AnimalResponse])
async def get_animals(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: AnimalStatus | None = Query(None),
    lot_id: uuid.UUID | None = Query(None),
    tag_number: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedResponse[AnimalResponse]:
    service = AnimalService(session)
    result = await service.get_animals(page, limit, status=status, lot_id=lot_id, tag_number=tag_number)
    return PaginatedResponse(
        data=[AnimalResponse.model_validate(a) for a in result["data"]],
        page=result["page"],
        limit=result["limit"],
        has_next=result["has_next"],
    )


@router.post("/bulk", response_model=AnimalBulkCreateResponse)
async def bulk_create_animals(
    http_request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> AnimalBulkCreateResponse:
    service = AnimalService(session)
    content_type = http_request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await http_request.json()
        request = AnimalBulkCreateRequest.model_validate(body)
        rows = [item.model_dump() for item in request.animals]
        result = await service.bulk_create_animals(rows)
        return AnimalBulkCreateResponse(**result)

    # CSV path (multipart/form-data)
    form = await http_request.form()
    file = form.get("file")
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode()))
    total_created = 0
    total_failed: list[dict] = []
    batch: list[dict] = []
    row_num = 1

    for raw in reader:
        try:
            batch.append({
                "tag_number": raw["tag_number"],
                "breed": Breed(raw["breed"]),
                "category": AnimalCategory(raw["category"]),
                "birth_date": datetime.strptime(raw["birth_date"], "%Y-%m-%d").date(),
                "lot_id": uuid.UUID(raw["lot_id"]),
                "occurred_at": datetime.fromisoformat(raw["occurred_at"]) if raw.get("occurred_at") else None,
            })
        except Exception as exc:
            total_failed.append({"row": row_num, "reason": str(exc)})

        if len(batch) >= _BATCH_SIZE:
            res = await service.bulk_create_animals(batch)
            total_created += res["created"]
            total_failed.extend(res["failed"])
            batch = []
        row_num += 1

    if batch:
        res = await service.bulk_create_animals(batch)
        total_created += res["created"]
        total_failed.extend(res["failed"])

    return AnimalBulkCreateResponse(created=total_created, failed=total_failed)


@router.post("/bulk/events", response_model=EventBulkCreateResponse)
async def bulk_create_events(
    http_request: Request,
    event_type: EventType = Query(..., alias="type"),
    session: AsyncSession = Depends(get_async_session),
) -> EventBulkCreateResponse:
    service = EventService(session)
    content_type = http_request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await http_request.json()
        request = EventBulkCreateRequest.model_validate(body)
        rows = [item.model_dump() for item in request.events]
        result = await service.bulk_create_events(event_type, rows)
        return EventBulkCreateResponse(**result)

    # CSV streaming path (multipart/form-data)
    form = await http_request.form()
    file = form.get("file")
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode()))
    total_created = 0
    total_failed: list[dict] = []
    batch: list[dict] = []
    row_num = 1

    for raw in reader:
        try:
            batch.append(_parse_csv_event_row(raw, event_type))
        except Exception as exc:
            total_failed.append({"row": row_num, "reason": str(exc)})

        if len(batch) >= _BATCH_SIZE:
            res = await service.bulk_create_events(event_type, batch)
            total_created += res["created"]
            total_failed.extend(res["failed"])
            batch = []
        row_num += 1

    if batch:
        res = await service.bulk_create_events(event_type, batch)
        total_created += res["created"]
        total_failed.extend(res["failed"])

    return EventBulkCreateResponse(created=total_created, failed=total_failed)


@router.get("/{animal_id}/history", response_model=PaginatedResponse[EventResponse])
async def get_animal_history(
    animal_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedResponse[EventResponse]:
    service = EventService(session)
    result = await service.get_animal_history(animal_id, page, limit)
    return PaginatedResponse(
        data=[EventResponse.model_validate(e) for e in result["data"]],
        page=result["page"],
        limit=result["limit"],
        has_next=result["has_next"],
    )
