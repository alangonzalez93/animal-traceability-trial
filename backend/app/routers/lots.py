import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.animal import AnimalResponse
from app.schemas.common import PaginatedResponse
from app.schemas.lot import AdgResponse, LotResponse
from app.services.lot_service import LotService

router = APIRouter(prefix="/lots", tags=["lots"])


@router.get("", response_model=PaginatedResponse[LotResponse])
async def get_lots(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    field_id: uuid.UUID | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedResponse[LotResponse]:
    service = LotService(session)
    result = await service.get_lots(page, limit, field_id=field_id)
    return PaginatedResponse(
        data=[LotResponse.model_validate(lot) for lot in result["data"]],
        page=result["page"],
        limit=result["limit"],
        has_next=result["has_next"],
    )


@router.get("/{lot_id}", response_model=LotResponse)
async def get_lot(
    lot_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> LotResponse:
    service = LotService(session)
    lot = await service.get_lot(lot_id)
    return LotResponse.model_validate(lot)


@router.get("/{lot_id}/animals")
async def get_lot_animals(
    lot_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    service = LotService(session)
    animals = await service.get_lot_animals(lot_id)
    return {"animals": [AnimalResponse.model_validate(a).model_dump() for a in animals]}


@router.get("/{lot_id}/adg", response_model=AdgResponse)
async def get_lot_adg(
    lot_id: uuid.UUID,
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    min_days: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> AdgResponse:
    service = LotService(session)
    result = await service.get_lot_adg(lot_id, from_, to, min_days)
    return AdgResponse(**result)
