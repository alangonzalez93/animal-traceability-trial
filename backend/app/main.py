from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.logging import configure_logging
from app.core.exceptions import unhandled_exception_handler
from app.routers import animals, lots


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    yield


app = FastAPI(title="Animal Traceability API", lifespan=lifespan)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(animals.router)
app.include_router(lots.router)
