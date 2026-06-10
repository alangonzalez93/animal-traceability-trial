import logging
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = str(uuid.uuid4())
    logger.exception("Unhandled error %s on %s %s", error_id, request.method, request.url)
    return JSONResponse(status_code=500, content={"error_id": error_id, "detail": "Internal server error"})
