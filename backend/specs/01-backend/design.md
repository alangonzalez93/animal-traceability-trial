# Design — Animal Traceability (MVP Backend)

**Date:** 2026-06-09
**Scope:** MVP backend. Stack: Python 3.12, FastAPI (async), SQLAlchemy 2 (async), Alembic, PostgreSQL 15+.

---

## Architecture

Layered architecture, identical to the reference project:

```
Request
  ↓
Router     (app/routers/*.py)       — HTTP validation, serialization
  ↓
Service    (app/services/*.py)      — business logic, coordination
  ↓
Repository (app/repositories/*.py) — data access (async)
  ↓
ORM Model  (app/models/*.py)       — SQLAlchemy table definitions
  ↓
PostgreSQL
```

---

## Directory structure

```
backend/
├── alembic/
│   ├── versions/               # Auto-generated migrations
│   ├── env.py                  # Alembic runtime config (async + settings)
│   └── script.py.mako          # Migration template
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── config/
│   │   ├── settings.py         # pydantic-settings (environment variables)
│   │   └── logging.py          # Structured logging
│   ├── core/
│   │   ├── database.py         # Declarative base + async engine + get_async_session
│   │   └── exceptions.py       # Global unhandled exception handler
│   ├── models/
│   │   ├── __init__.py         # Re-exports all models (required by Alembic autogenerate)
│   │   ├── base_model.py       # AuditMixin (id, created_at, updated_at, deleted)
│   │   ├── field.py
│   │   ├── lot.py
│   │   ├── animal.py
│   │   ├── event.py
│   │   ├── animal_lot_period.py
│   │   └── enums.py            # AnimalStatus, EventType, Breed, AnimalCategory
│   ├── schemas/
│   │   ├── animal.py
│   │   ├── event.py
│   │   ├── lot.py
│   │   └── common.py           # PaginatedResponse
│   ├── repositories/
│   │   ├── base.py             # Generic BaseRepository[T]
│   │   ├── animal_repository.py
│   │   ├── event_repository.py
│   │   ├── lot_repository.py
│   │   └── animal_lot_period_repository.py
│   ├── services/
│   │   ├── animal_service.py
│   │   ├── event_service.py
│   │   └── lot_service.py
│   ├── routers/
│   │   ├── animals.py
│   │   └── lots.py
│   └── scripts/
│       └── seed.py             # Seeder with historical data for ADG queries
├── tests/
│   ├── conftest.py             # testcontainers PostgreSQL + fixtures
│   ├── test_animals.py
│   ├── test_events.py
│   └── test_lots.py
├── specs/
│   └── 01-backend/
│       ├── requirements.md
│       ├── design.md           ← this file
│       └── tasks.md
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── docker-compose.yml
├── docker-compose.override.yml
├── Dockerfile
├── .env.example
└── .pre-commit-config.yaml
```

---

## Data model

### ERD

```
fields (1) ──── (N) lots (1) ──── (N) animal_lot_periods
                                             │
                     animals (1) ────────────┤
                         │                   │
                         └──── (N) events    └──── (N) lots
```

---

### AuditMixin (`app/models/base_model.py`)

All tables except `events` inherit this mixin. Must come before `Base` in the MRO.

```python
class AuditMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    deleted: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Animal(AuditMixin, Base):
    __tablename__ = "animals"
```

---

### fields

```sql
fields (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted     BOOLEAN NOT NULL DEFAULT FALSE
)
```

---

### lots

```sql
lots (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_id    UUID NOT NULL REFERENCES fields(id),
    name        VARCHAR NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted     BOOLEAN NOT NULL DEFAULT FALSE
)
```

---

### animals

```sql
animals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_number      VARCHAR NOT NULL,
    breed           VARCHAR NOT NULL,
    category        VARCHAR NOT NULL,
    status          VARCHAR NOT NULL DEFAULT 'ACTIVE',
    birth_date      DATE,
    current_lot_id  UUID REFERENCES lots(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted         BOOLEAN NOT NULL DEFAULT FALSE
)
```

**Decisions:**
- `tag_number` is the physical ear tag, mutable. The UUID is the permanent identity of the animal.
- `category`, `status` and `current_lot_id` are projections — updated on each relevant event but events are the source of truth.
- `status` (`ACTIVE | DEAD | SOLD`) exists to make filtering efficient without scanning events.
- `updated_at` serves as the logical deletion date when `deleted = true`.

**Python-validated enums** (`app/models/enums.py`):
- `AnimalStatus`: `ACTIVE`, `DEAD`, `SOLD`
- `AnimalCategory`: `CALF`, `STEER`, `COW`, `BULL`, `HEIFER`
- `Breed`: `ANGUS`, `HEREFORD`, `BRAHMAN`, `LIMOUSIN`, `SHORTHORN`, `CRIOLLO`

---

### events

```sql
events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id   UUID NOT NULL REFERENCES animals(id),
    type        VARCHAR NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}'
)
```

**Events are immutable** — they have no `updated_at` or `deleted`. Do not inherit `AuditMixin`.

**Valid types:** `BIRTH | MOVE | DEATH | SALE | RECLASSIFICATION | WEIGHT | VACCINATION`

**Payload by type:**
```
BIRTH           → {}
MOVE            → { "from_lot_id": "uuid", "to_lot_id": "uuid" }
WEIGHT          → { "weight_kg": "312.50" }   ← string to preserve Decimal precision in JSONB
VACCINATION     → { "vaccine_name": "FMD" }
DEATH           → { "cause": "..." }
SALE            → {}
RECLASSIFICATION→ { "previous_category": "CALF", "new_category": "STEER" }
```

> `weight_kg` is serialized as a string in JSONB to preserve `Decimal` precision. When reading, cast with `(payload->>'weight_kg')::numeric`. The expression index uses exactly that cast — if the ORM generates `CAST(...)` instead of `::numeric`, the index is silently ignored.

**CHECK constraints (in Alembic migration):**
```sql
CHECK (type IN ('BIRTH','MOVE','DEATH','SALE','RECLASSIFICATION','WEIGHT','VACCINATION'))
CHECK (type != 'MOVE' OR (payload ? 'from_lot_id' AND payload ? 'to_lot_id'))
CHECK (type != 'WEIGHT' OR payload ? 'weight_kg')
CHECK (type != 'VACCINATION' OR payload ? 'vaccine_name')
CHECK (type != 'RECLASSIFICATION' OR (payload ? 'previous_category' AND payload ? 'new_category'))
```

---

### animal_lot_periods

```sql
animal_lot_periods (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    animal_id   UUID NOT NULL REFERENCES animals(id),
    lot_id      UUID NOT NULL REFERENCES lots(id),
    entered_at  TIMESTAMPTZ NOT NULL,
    exited_at   TIMESTAMPTZ,              -- NULL = animal is still in this lot
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

**Why it exists:** Without this table, calculating the ADG for the lot where an animal was during the measurement period requires reconstructing its position from all its MOVE events — not viable in real time with 500k animals.

**How it is maintained** (within the same transaction as the MOVE event):
1. Close active period: `UPDATE ... SET exited_at = occurred_at WHERE animal_id = X AND exited_at IS NULL`
2. Open new period: `INSERT INTO animal_lot_periods (animal_id, lot_id, entered_at)`

Does not fully inherit `AuditMixin` (no `deleted`) but does have `id`, `created_at`, `updated_at`.

---

## Indexes (in Alembic migrations)

```sql
-- ADG star query: covering index with JSONB expression
-- CRITICAL: the query must use (payload->>'weight_kg')::numeric exactly
CREATE INDEX idx_events_weight
ON events (animal_id, occurred_at, (payload->>'weight_kg')::numeric)
WHERE type = 'WEIGHT';

-- Complete animal history
CREATE INDEX idx_events_by_animal
ON events (animal_id, occurred_at);

-- Vaccination correlation
CREATE INDEX idx_events_vaccination
ON events (animal_id, occurred_at)
WHERE type = 'VACCINATION';

-- Movement reconstruction
CREATE INDEX idx_events_move
ON events (animal_id, occurred_at)
WHERE type = 'MOVE';

-- An animal can only have one open period at a time (second line of defense after SELECT FOR UPDATE)
CREATE UNIQUE INDEX idx_animal_lot_periods_single_open
ON animal_lot_periods (animal_id)
WHERE exited_at IS NULL;

-- Individual history (ADG for a specific animal)
CREATE INDEX idx_animal_lot_periods_by_animal
ON animal_lot_periods (animal_id, entered_at, exited_at);

-- ADG star query by lot — the most important index in the system
-- Without it: full scan of animal_lot_periods before any other operation
CREATE INDEX idx_animal_lot_periods_by_lot
ON animal_lot_periods (lot_id, entered_at, exited_at);

-- Current lot status (active animals)
CREATE INDEX idx_animals_current_lot
ON animals (current_lot_id)
WHERE status = 'ACTIVE' AND deleted = FALSE;
```

Expression indexes (`idx_events_weight`) and partial indexes (`WHERE type = ...`) **cannot be autogenerated by Alembic** — they must be defined manually in the migration with `op.execute("CREATE INDEX ...")`.

---

## Alembic configuration

Same configuration as the reference project. Key points:

### `alembic/env.py`

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models  # noqa: F401 — registers all models in Base.metadata for autogenerate
from alembic import context
from app.config.settings import settings
from app.core.database import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)  # overrides placeholder in alembic.ini

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # NullPool required for async migrations: avoids pool conflicts with asyncio.run()
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

### `app/models/__init__.py`

This file is the single model registration point for Alembic autogenerate. When adding a new model, only import it here.

```python
from app.models.field import Field
from app.models.lot import Lot
from app.models.animal import Animal
from app.models.event import Event
from app.models.animal_lot_period import AnimalLotPeriod
from app.models.enums import AnimalStatus, EventType, Breed, AnimalCategory

__all__ = ["Field", "Lot", "Animal", "Event", "AnimalLotPeriod", ...]
```

### `app/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Engine and sessionmaker created once on import; FastAPI lifespan validates the connection
```

### Migration workflow

```bash
# Create migration (autogenerates from models)
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

**Rule:** expression and partial indexes must be added manually with `op.execute()` in the initial migration, as Alembic does not autogenerate them.

---

## Docker Compose

The `api` service runs `alembic upgrade head` before starting uvicorn. The `&&` ensures migrations fail explicitly before the app starts.

```yaml
api:
  build: .
  command: >
    sh -c "alembic upgrade head &&
           uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
  env_file: .env
  depends_on:
    db:
      condition: service_healthy
```

---

## Environment variables (`.env.example`)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://traceability:traceability@db:5432/animal_traceability

# App
ENV=development
LOG_LEVEL=INFO
```

### `app/config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    database_url: str
    env: str = "development"
    log_level: str = "INFO"

settings = Settings()
```

---

## API contracts

### POST /animals/bulk

Accepts JSON or CSV. Each row/object includes `lot_id` and `occurred_at` — allows creating animals in different lots in a single operation and importing historical data.

**JSON request:**
```json
{
  "animals": [
    {
      "tag_number": "AR001",
      "breed": "ANGUS",
      "category": "CALF",
      "birth_date": "2024-06-01",
      "lot_id": "uuid-lot-1",
      "occurred_at": "2025-01-15T08:00:00Z"  // optional, defaults to NOW()
    }
  ]
}
```

**CSV request** (`multipart/form-data`, field `file`):
```csv
tag_number,breed,category,birth_date,lot_id,occurred_at
AR001,ANGUS,CALF,2024-06-01,uuid-lot-1,2025-01-15T08:00:00Z
AR002,HEREFORD,COW,2022-03-15,uuid-lot-2,
```

`occurred_at` is optional — empty cell defaults to `NOW()`. Allows mixing historical and new animals in the same file.

CSV is processed in streaming with batches of 1000 rows — same strategy as `/bulk/events`.

**Response 201:**
```json
{
  "created": 98,
  "failed": [{ "row": 3, "reason": "lot_id not found" }]
}
```

**SQL — 3 operations per batch in one transaction:**
```sql
-- 1. Insert animals, capture generated IDs
INSERT INTO animals (tag_number, breed, category, status, current_lot_id, birth_date)
SELECT UNNEST($1::varchar[]), UNNEST($2::varchar[]), UNNEST($3::varchar[]),
       'ACTIVE', UNNEST($4::uuid[]), UNNEST($5::date[])
RETURNING id;

-- 2. Register BIRTH event for each animal
INSERT INTO events (animal_id, type, occurred_at, payload)
SELECT UNNEST($ids::uuid[]), 'BIRTH', UNNEST($6::timestamptz[]), '{}';

-- 3. Open initial animal_lot_period
INSERT INTO animal_lot_periods (animal_id, lot_id, entered_at)
SELECT UNNEST($ids::uuid[]), UNNEST($4::uuid[]), UNNEST($6::timestamptz[]);
```

---

### POST /animals/bulk/events

Single endpoint for all event types, including MOVE. Accepts JSON (small payload) or CSV (hundreds of thousands of rows).

**JSON request:**
```json
{
  "animal_ids": ["uuid"],
  "type": "WEIGHT",
  "occurred_at": "2025-02-10T07:00:00Z",
  "payload": { "weight_kg": "312.50" }
}
```

**JSON request (MOVE):**
```json
{
  "animal_ids": ["uuid", "uuid"],
  "type": "MOVE",
  "occurred_at": "2025-03-01T06:00:00Z",
  "payload": { "from_lot_id": "uuid", "to_lot_id": "uuid" }
}
```

**CSV request** (`multipart/form-data`, field `file`, with query param `?type=<TYPE>`):

Each event type has its own column format — no embedded JSON, no empty columns.

```
POST /animals/bulk/events?type=WEIGHT
POST /animals/bulk/events?type=MOVE
POST /animals/bulk/events?type=VACCINATION
...
```

| Type | CSV columns |
|---|---|
| `WEIGHT` | `animal_id, occurred_at, weight_kg` |
| `MOVE` | `animal_id, occurred_at, from_lot_id, to_lot_id` |
| `VACCINATION` | `animal_id, occurred_at, vaccine_name` |
| `DEATH` | `animal_id, occurred_at, cause` |
| `SALE` | `animal_id, occurred_at` |
| `RECLASSIFICATION` | `animal_id, occurred_at, previous_category, new_category` |

**Examples:**

```csv
-- WEIGHT
animal_id,occurred_at,weight_kg
uuid1,2025-02-10T07:00:00Z,312.50
uuid2,2025-02-10T07:00:00Z,298.00

-- MOVE
animal_id,occurred_at,from_lot_id,to_lot_id
uuid1,2025-03-01T06:00:00Z,uuid-a,uuid-b

-- VACCINATION
animal_id,occurred_at,vaccine_name
uuid1,2025-02-01T09:00:00Z,FMD

-- RECLASSIFICATION
animal_id,occurred_at,previous_category,new_category
uuid1,2025-06-01T09:00:00Z,CALF,STEER
```

**CSV processing — streaming + batching:**
- The type is taken from the `?type=` query param and used to know which columns to parse.
- The file is read line by line (never fully loaded into memory).
- Rows are accumulated in batches of 1000.
- Each batch builds the corresponding JSONB `payload` for the type and calls `event_service.bulk_create_events` — same logic as JSON.
- The response is synchronous: the client waits until all rows are processed.

**Response 201:**
```json
{
  "created": 94872,
  "failed": [{ "row": 1041, "animal_id": "uuid", "reason": "animal not found" }]
}
```

**Internal dispatch by type (event_service):**
- `MOVE` → 5 SQL operations in one transaction (see below)
- `DEATH` / `SALE` → insert event + UPDATE animals.status
- `RECLASSIFICATION` → insert event + UPDATE animals.category
- `WEIGHT`, `VACCINATION`, `BIRTH` → insert event

**5 SQL operations for MOVE (one transaction):**
```sql
-- 0. Lock to serialize concurrent movements on the same animals
SELECT id FROM animals WHERE id = ANY($1::uuid[]) FOR UPDATE;

-- 1. MOVE event
INSERT INTO events (animal_id, type, occurred_at, payload)
SELECT UNNEST($1::uuid[]), 'MOVE', $4,
       jsonb_build_object('from_lot_id', $2::text, 'to_lot_id', $3::text);

-- 2. Projection on animals
UPDATE animals SET current_lot_id = $3, updated_at = $4
WHERE id = ANY($1::uuid[]);

-- 3. Close active period
UPDATE animal_lot_periods SET exited_at = $4, updated_at = $4
WHERE animal_id = ANY($1::uuid[]) AND exited_at IS NULL;

-- 4. Open new period
INSERT INTO animal_lot_periods (animal_id, lot_id, entered_at)
SELECT UNNEST($1::uuid[]), $3, $4;
```

---

### GET /animals/{id}/history

**Query params:** `page=1&limit=50`

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "type": "WEIGHT",
      "occurred_at": "2025-02-10T07:00:00Z",
      "payload": { "weight_kg": "312.50" }
    }
  ],
  "page": 1,
  "limit": 50,
  "has_next": true
}
```

**SQL:**
```sql
SELECT id, type, occurred_at, payload
FROM events
WHERE animal_id = $1
ORDER BY occurred_at DESC
LIMIT $2 OFFSET $3;
```

Uses `idx_events_by_animal`. SLA < 50ms.

---

### GET /lots/{id}/animals

**Response 200:**
```json
{
  "lot_id": "uuid",
  "lot_name": "Pasture 3",
  "animals": [
    {
      "id": "uuid",
      "tag_number": "AR001",
      "breed": "ANGUS",
      "category": "STEER",
      "status": "ACTIVE",
      "birth_date": "2024-06-01"
    }
  ]
}
```

---

### GET /lots/{id}/adg

**Query params:** `from=2025-01-01&to=2025-03-31&min_days=15`

**Response 200:**
```json
{
  "lot_id": "uuid",
  "lot_name": "Pasture 3",
  "period": { "from": "2025-01-01", "to": "2025-03-31" },
  "animals_count": 143,
  "avg_adg_kg_day": 0.92
}
```

**ADG query (CTEs):**
```sql
WITH lot_periods AS (
    -- idx_animal_lot_periods_by_lot: direct index seek by lot_id
    SELECT animal_id, entered_at, COALESCE(exited_at, $3) AS exited_at
    FROM animal_lot_periods
    WHERE lot_id = $1
      AND entered_at < $3
      AND (exited_at IS NULL OR exited_at > $2)
),
first_weight AS (
    -- idx_events_weight: covering index (animal_id, occurred_at, weight_kg::numeric)
    SELECT DISTINCT ON (e.animal_id)
        e.animal_id,
        e.occurred_at AS weighed_at,
        (e.payload->>'weight_kg')::numeric AS weight_kg  -- CRITICAL: exact ::numeric cast
    FROM events e
    JOIN lot_periods lp ON e.animal_id = lp.animal_id
    WHERE e.type = 'WEIGHT'
      AND e.occurred_at >= GREATEST(lp.entered_at, $2)
      AND e.occurred_at <  lp.exited_at
      AND e.occurred_at >= $2
    ORDER BY e.animal_id, e.occurred_at ASC
),
last_weight AS (
    SELECT DISTINCT ON (e.animal_id)
        e.animal_id,
        e.occurred_at AS weighed_at,
        (e.payload->>'weight_kg')::numeric AS weight_kg
    FROM events e
    JOIN lot_periods lp ON e.animal_id = lp.animal_id
    WHERE e.type = 'WEIGHT'
      AND e.occurred_at >= GREATEST(lp.entered_at, $2)
      AND e.occurred_at <  lp.exited_at
      AND e.occurred_at <= $3
    ORDER BY e.animal_id, e.occurred_at DESC
),
adg_per_animal AS (
    SELECT
        f.animal_id,
        (l.weight_kg - f.weight_kg) / NULLIF(EXTRACT(EPOCH FROM (l.weighed_at - f.weighed_at)) / 86400, 0) AS adg
    FROM first_weight f
    JOIN last_weight l ON f.animal_id = l.animal_id
    WHERE EXTRACT(EPOCH FROM (l.weighed_at - f.weighed_at)) / 86400 >= $4  -- min_days
)
SELECT
    COUNT(*)            AS animals_count,
    AVG(adg)            AS avg_adg_kg_day
FROM adg_per_animal;
```

**Expected performance:**

| CTE | PostgreSQL operation | Index used |
|---|---|---|
| `lot_periods` | Index seek + range scan | `idx_animal_lot_periods_by_lot` |
| `first_weight` | Index seek by animal + ordered scan | `idx_events_weight` (covering) |
| `last_weight` | Same, reverse order | `idx_events_weight` |
| `adg_per_animal` | In-memory hash join | — |
| Final SELECT | Aggregation | — |

Estimated: < 100ms for 1,000 animals with indexes.

---

## Seeder (`app/scripts/seed.py`)

The seeder uses direct inserts via `UNNEST` with `occurred_at` distributed over time (not `NOW()`). This is what allows ADG queries with historical date filters to return real data.

All dates are within **2026-01-01 – 2026-06-10** (`RANGE_START` / `RANGE_END`).

Generated data:
- 2 fields, 6 lots
- 500 animals distributed across lots
- `birth_date`: 1–15 days before registration (within 2026-01-01 – 2026-01-20)
- BIRTH events (`occurred_at`): 2026-01-01 – 2026-01-20 (registration window)
- 3 WEIGHT cycles per animal ~45 days apart:
  - Cycle 0: ~2026-01-31 (day 30 ± 5)
  - Cycle 1: ~2026-03-17 (day 75 ± 5)
  - Cycle 2: ~2026-05-01 (day 120 ± 5)
- VACCINATION events: ~2026-02-19 (day 50 ± 5), 100 animals
- MOVE events: ~2026-05-11 (day 130 ± 5), 50 animals

After completion:
```sql
ANALYZE events;
ANALYZE animal_lot_periods;
```

Required so the query planner has correct statistics when showing EXPLAIN ANALYZE. Without this, row estimates are incorrect even if the correct indexes are used.

---

## Critical data types

| Field | PostgreSQL | Python / Pydantic | Reason |
|---|---|---|---|
| `weight_kg` | `NUMERIC` (via JSONB cast) | `Decimal` | `float` accumulates rounding errors in ADG across thousands of weighings |
| IDs | `UUID` | `UUID` | Permanent identity independent of external systems |
| Dates | `TIMESTAMPTZ` | `datetime` (aware) | Explicit timezone, avoids ambiguity in comparisons |

---

## V2 — documented, not implemented

| Feature | Decision |
|---|---|
| RANGE partitioning by year on `events (occurred_at)` | Designed to be added without schema changes. Partial indexes mitigate impact in MVP. |
| `animal_period_summaries` | Pre-calculated ADG per category period, updated on each RECLASSIFICATION. |
| `animal_tags` | Physical ear tag history. Schema documented in requirements. |
| BigQuery pipeline | Analytical queries without impact on the operational database. |
| CSV upload with COPY + staging table | For 500k+ row loads, asyncpg's `COPY FROM STDIN` is ~10x faster than UNNEST batches (one operation vs 500 round-trips). Pattern: COPY → temp staging table → bulk SQL validation → final INSERT → UPDATE projections. Not implemented in MVP because UNNEST batches of 1000 are sufficient for current volume and the added complexity is not justified. |
