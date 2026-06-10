import os
import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

_BACKEND_DIR = Path(__file__).parent.parent

# Tables ordered so TRUNCATE CASCADE has no dependency conflicts.
_TRUNCATE = "TRUNCATE TABLE events, animal_lot_periods, animals, lots, fields CASCADE"


# ─── Session-scoped (sync) ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def pg():
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def db_url(pg):
    return pg.get_connection_url(driver="asyncpg")


@pytest.fixture(scope="session", autouse=True)
def run_migrations(db_url):
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": db_url},
        cwd=str(_BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Alembic failed:\n{result.stderr}\n{result.stdout}"


# ─── Per-test session — commits are real, tables are wiped after each test ─────

@pytest.fixture
async def session(db_url):
    engine = create_async_engine(db_url, poolclass=NullPool)
    sess = AsyncSession(engine, expire_on_commit=False)
    yield sess
    await sess.close()
    async with AsyncSession(engine) as cleanup:
        async with cleanup.begin():
            await cleanup.execute(text(_TRUNCATE))
    await engine.dispose()


# ─── HTTP client wired to the test session ────────────────────────────────────

@pytest.fixture
async def client(session):
    from app.core.database import get_async_session
    from app.main import app

    async def _override():
        yield session

    app.dependency_overrides[get_async_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ─── Seeding helpers ───────────────────────────────────────────────────────────

@pytest.fixture
async def lot(session):
    async with session.begin():
        r = await session.execute(
            text("INSERT INTO fields (name) VALUES ('Test Field') RETURNING id")
        )
        field_id = r.scalar_one()
        r = await session.execute(
            text("INSERT INTO lots (name, field_id) VALUES ('Test Lot', :fid) RETURNING id"),
            {"fid": str(field_id)},
        )
        return r.scalar_one()


@pytest.fixture
async def lot_pair(session):
    async with session.begin():
        r = await session.execute(
            text("INSERT INTO fields (name) VALUES ('Field B') RETURNING id")
        )
        fid = r.scalar_one()
        r = await session.execute(
            text("INSERT INTO lots (name, field_id) VALUES ('Lot A', :fid) RETURNING id"),
            {"fid": str(fid)},
        )
        lot_a = r.scalar_one()
        r = await session.execute(
            text("INSERT INTO lots (name, field_id) VALUES ('Lot B', :fid) RETURNING id"),
            {"fid": str(fid)},
        )
        lot_b = r.scalar_one()
        return lot_a, lot_b
