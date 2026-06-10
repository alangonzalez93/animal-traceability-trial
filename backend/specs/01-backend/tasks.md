# Tasks — Animal Traceability (MVP Backend)

**Date:** 2026-06-09
**Refs:** requirements.md, design.md

Ordered implementation checklist. Each task is a discrete, verifiable step.

---

## Phase 1 — Project setup

- [ ] **1.1** Initialize project with `uv init` in `/backend`
- [ ] **1.2** Configure `pyproject.toml`:
  - `requires-python = ">=3.12"`
  - dependencies: `fastapi[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`
  - dev dependencies: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `testcontainers[postgres]`, `pre-commit`
  - sections `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.pytest.ini_options]`
- [ ] **1.3** Create `.pre-commit-config.yaml` with `ruff` and `ruff-format` hooks
- [ ] **1.4** Create `.env.example` with `DATABASE_URL`, `ENV`, `LOG_LEVEL`
- [ ] **1.5** Create `.gitignore` (include `.env`, `__pycache__/`, `.venv/`, `.ruff_cache/`, `.pytest_cache/`)
- [ ] **1.6** Create `docker-compose.yml` with services `db` (postgres:16-alpine with healthcheck) and `api`
- [ ] **1.7** Create multi-stage `Dockerfile` (builder with uv + runtime with non-root user)
- [ ] **1.8** Verify `docker compose up` starts without errors

---

## Phase 2 — Base infrastructure

- [ ] **2.1** Create `app/config/settings.py` with `pydantic-settings` (`database_url`, `env`, `log_level`)
- [ ] **2.2** Create `app/config/logging.py` with structured logging configurable by `LOG_LEVEL`
- [ ] **2.3** Create `app/core/database.py`: `DeclarativeBase`, `create_async_engine`, `async_sessionmaker`, `get_async_session` (dependency)
- [ ] **2.4** Create `app/core/exceptions.py`: global handler that logs with a UUID `error_id` and returns 500
- [ ] **2.5** Create `app/main.py`: `FastAPI` app with lifespan, register routers and exception handler
- [ ] **2.6** Verify the app starts without errors

---

## Phase 3 — ORM models

- [ ] **3.1** Create `app/models/enums.py`: `AnimalStatus`, `EventType`, `Breed`, `AnimalCategory`
- [ ] **3.2** Create `app/models/base_model.py`: `AuditMixin` (`id`, `deleted`, `created_at`, `updated_at`)
- [ ] **3.3** Create `app/models/field.py`: `Field` model with `AuditMixin`
- [ ] **3.4** Create `app/models/lot.py`: `Lot` model with FK to `fields`
- [ ] **3.5** Create `app/models/animal.py`: `Animal` model with `tag_number`, `breed`, `category`, `status`, `birth_date`, `current_lot_id`
- [ ] **3.6** Create `app/models/event.py`: `Event` model without `AuditMixin` (immutable — only `id`, `animal_id`, `type`, `occurred_at`, `payload`)
- [ ] **3.7** Create `app/models/animal_lot_period.py`: `AnimalLotPeriod` model (`id`, `animal_id`, `lot_id`, `entered_at`, `exited_at`, `created_at`, `updated_at`) — no `deleted`, no `AuditMixin`
- [ ] **3.8** Create `app/models/__init__.py`: import all models (single registration point for Alembic autogenerate)

---

## Phase 4 — Alembic

- [ ] **4.1** Initialize Alembic: `uv run alembic init alembic`
- [ ] **4.2** Configure `alembic/env.py`:
  - `import app.models` (registers models in `Base.metadata`)
  - `config.set_main_option("sqlalchemy.url", settings.database_url)`
  - `target_metadata = Base.metadata`
  - online mode with `async_engine_from_config` + `NullPool`
- [ ] **4.3** Autogenerate initial migration: `uv run alembic revision --autogenerate -m "initial"`
- [ ] **4.4** Review generated migration — manually add with `op.execute()`:
  - CHECK constraints for `events` (type, move, weight, vaccination, reclassification)
  - All partial and expression indexes (see list in design.md)
  - `idx_animal_lot_periods_single_open` (partial UNIQUE)
- [ ] **4.5** Apply migration: `uv run alembic upgrade head`
- [ ] **4.6** Verify all tables and indexes exist in the DB

---

## Phase 5 — Repositories

- [ ] **5.1** Create `app/repositories/base.py`: `BaseRepository[T]` with `get_by_id`, `get_all`, `create`
- [ ] **5.2** Create `app/repositories/lot_repository.py`: `get_by_id` (with `deleted=False`), `get_animals_by_lot`
- [ ] **5.3** Create `app/repositories/animal_repository.py`:
  - `bulk_create` (UNNEST, returns created IDs)
  - `bulk_update` (ANY, accepts `**fields` — single UPDATE for `current_lot_id`, `status`, `category`, etc.)
  - `lock_for_update` (SELECT ... FOR UPDATE on a list of IDs — first step of bulk move)
- [ ] **5.4** Create `app/repositories/event_repository.py`:
  - `bulk_create` (UNNEST)
  - `get_history` (paginated, ORDER BY `occurred_at DESC`)
  - `get_adg` (full CTE query from design.md)
- [ ] **5.5** Create `app/repositories/animal_lot_period_repository.py`:
  - `bulk_close_active` (ANY, closes periods with `exited_at IS NULL`)
  - `bulk_open` (UNNEST, opens new periods)
  - `bulk_create_initial` (UNNEST, for bulk animal registration)

---

## Phase 6 — Services

- [ ] **6.1** Create `app/services/animal_service.py`:
  - `bulk_create_animals`: validates `lot_id`, inserts animals, opens `animal_lot_periods`, registers BIRTH events — all in one transaction. Returns `{created, failed}`.
- [ ] **6.2** Create `app/services/event_service.py`:
  - `get_animal_history`: returns paginated events for an animal (validates existence, delegates to repository)
  - `bulk_create_events`: single entry point for all event types. Dispatches internally by type:
    - `MOVE` → `lock_for_update` → insert event → `bulk_update(current_lot_id)` → `bulk_close_active` → `bulk_open` (5 ops, one transaction)
    - `DEATH` / `SALE` → insert event + `bulk_update(status)`
    - `RECLASSIFICATION` → insert event + `bulk_update(category)`
    - `WEIGHT`, `VACCINATION`, `BIRTH` → insert event
  - Returns `{created, failed}`.
- [ ] **6.3** Create `app/services/lot_service.py`:
  - `get_lot_animals`: returns active animals in the lot
  - `get_lot_adg`: executes CTE query, returns ADG schema

---

## Phase 7 — Routers and schemas

- [ ] **7.1** Create `app/schemas/common.py`: `PaginatedResponse[T]`
- [ ] **7.2** Create `app/schemas/animal.py`: `AnimalBulkCreateRequest` (JSON, list of objects with `lot_id` and `occurred_at` per item), `AnimalBulkCreateResponse`, `AnimalResponse`
- [ ] **7.3** Create `app/schemas/event.py`: `EventBulkCreateRequest` (JSON), `EventBulkCreateResponse`, `EventResponse`
- [ ] **7.4** Create `app/schemas/lot.py`: `LotAnimalsResponse`, `AdgResponse`
- [ ] **7.5** Create `app/routers/animals.py`:
  - `POST /animals/bulk` → `animal_service.bulk_create_animals` (JSON and CSV; `lot_id` and `occurred_at` per row)
  - `POST /animals/bulk/events` → `event_service.bulk_create_events`
    - JSON (`Content-Type: application/json`): processes directly
    - CSV (`multipart/form-data` + `?type=<TYPE>`): stream line by line, parse columns by type (see table in design.md), batches of 1000, build JSONB payload and call the same service per batch
  - `GET /animals/{id}/history` → `event_service.get_animal_history` (paginated)
- [ ] **7.6** Create `app/routers/lots.py`:
  - `GET /lots/{id}/animals` → `lot_service.get_lot_animals`
  - `GET /lots/{id}/adg` → `lot_service.get_lot_adg`
- [ ] **7.7** Register all routers in `app/main.py`

---

## Phase 8 — Seeder

- [ ] **8.1** Create `app/scripts/seed.py`:
  - Insert 2 fields and 6 lots with UNNEST
  - Insert 500 animals distributed across lots (via `POST /animals/bulk` or direct UNNEST) with `occurred_at` between 2023-01-01 and 2024-06-01
  - Register 3 weighing cycles (WEIGHT) per animal ~45 days apart via `POST /animals/bulk/events`
  - Interleave MOVE, VACCINATION and RECLASSIFICATION events with coherent historical dates
  - Execute `ANALYZE events` and `ANALYZE animal_lot_periods` at the end
- [ ] **8.2** Verify that `GET /lots/{id}/adg?from=2026-01-01&to=2026-06-10&min_days=15` returns `animals_count > 0`

---

## Phase 9 — Tests

- [ ] **9.1** Create `tests/conftest.py`: `postgres_url` fixture (testcontainers), `db_session` fixture (transaction rollback), `client` fixture (httpx + `get_async_session` override)
- [ ] **9.2** Create `tests/test_animals.py`:
  - Bulk registration: verifies `created` count, BIRTH event generated, `animal_lot_period` opened
  - Bulk move: verifies MOVE event, `current_lot_id` projection, period closed and new one opened
  - Concurrent move: two bulk moves on the same animals do not generate a double open period
- [ ] **9.3** Create `tests/test_events.py`:
  - Bulk WEIGHT events: verifies insertion and that `weight_kg` is stored as string in JSONB
  - Bulk DEATH events: verifies `status` is updated to `DEAD`
  - Bulk RECLASSIFICATION events: verifies `category` is updated
  - Invalid payload: returns 422 with missing field detail
- [ ] **9.4** Create `tests/test_lots.py`:
  - `GET /lots/{id}/animals`: returns only animals with `status = ACTIVE`
  - `GET /lots/{id}/adg`: returns correct `avg_adg_kg_day` for known test data
  - `GET /lots/{id}/adg` without sufficient weighings: returns `animals_count = 0`
- [ ] **9.5** Verify `uv run pytest tests/ -v` passes green

---

## Phase 10 — EXPLAIN ANALYZE

- [ ] **10.1** With seeder run and `ANALYZE` executed, run and document query plans for the 3 critical queries:
  - `GET /animals/{id}/history` — verify use of `idx_events_by_animal`
  - `GET /lots/{id}/animals` — verify use of `idx_animals_current_lot`
  - `GET /lots/{id}/adg` — verify use of `idx_animal_lot_periods_by_lot` and `idx_events_weight`
- [ ] **10.2** Confirm no plan includes `Seq Scan` on large tables (`events`, `animal_lot_periods`)
- [ ] **10.3** Document plans in `specs/01-backend/explain_analyze.md`
