# Animal Traceability

Livestock traceability system with bulk CSV ingestion, event history, and Average Daily Gain (ADG) analytics.

**Stack:** FastAPI · SQLAlchemy 2 (async) · PostgreSQL 16 · Alembic · React · uv

---

## Architecture

### Transaction ownership

Service methods own transaction boundaries (`async with self.session.begin()`). Repositories only execute queries — they never open or commit transactions. This means every multi-step write (insert animals + create BIRTH event + open lot period) is atomic by construction, and repositories remain composable without nested transaction surprises.

### Bulk operations

All bulk writes use PostgreSQL `UNNEST`-based statements — a single INSERT or UPDATE for an entire batch, regardless of size. CSV uploads are processed in batches of 1 000 rows, each batch in its own transaction, so a failure in batch N does not roll back batch N−1.

### N+1 prevention

- Animal and lot lookups that drive bulk writes use `IN (...)` queries built once per batch, not per-row `SELECT`.
- Event rows that arrive with `tag_number` are resolved to UUIDs in a single `WHERE tag_number IN (...)` query before any write happens.
- Lot validation in `bulk_create_animals` fetches all unique lot IDs in one query.

### Indexes

| Index | Purpose |
|---|---|
| `idx_animals_current_lot` (partial) | Fast lot membership queries — only indexes active, non-deleted animals |
| `idx_events_weight_adg` (partial) | ADG window queries — only indexes `WEIGHT` events, covering `(animal_id, occurred_at)` |

### Deadlock prevention

`lock_for_update` acquires row locks in primary-key order (`.order_by(Animal.id)`) so concurrent transactions always take locks in the same sequence.

---

## Prerequisites

| Tool | Version |
|---|---|
| Docker + Docker Compose | any recent version |
| [uv](https://docs.astral.sh/uv/) | ≥ 0.5 |
| Python | 3.12 (managed by uv) |

---

## Running the project

### 1. Clone and configure

```bash
git clone <repo-url>
cd animal-traceability-trial
cp backend/.env.example backend/.env
```

The defaults connect to the Compose-managed database — no changes needed.

### 2. Start all services

```bash
docker compose up --build
```

This starts three containers:

- **db** — PostgreSQL 16
- **api** — runs Alembic migrations then starts the API on port 8000
- **web** — React dev server on port 5173

Migrations run automatically on every `api` container start (before uvicorn starts).

- Frontend: [http://localhost:5173](http://localhost:5173)
- API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Loading fixture data (for FE testing)

The fixture files contain **50 000 animals**, **200 000 weight events** (4 per animal), and **50 000 vaccination events**. They are committed to the repository at `backend/tests/fixtures/`.

### Step 1 — Seed field and lots (run once)

The CSV files reference 10 fixed lot UUIDs. Run this script once with the stack up:

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://traceability:traceability@localhost:5432/animal_traceability \
uv run python -m app.scripts.seed
```

The script is idempotent — safe to run multiple times.

### Step 2 — Upload via the frontend

Open [http://localhost:5173](http://localhost:5173) and use the bulk upload UI to load the fixture files in order:

1. `backend/tests/fixtures/animals.csv`
2. `backend/tests/fixtures/events_weight.csv` (event type: `WEIGHT`)
3. `backend/tests/fixtures/events_vaccination.csv` (event type: `VACCINATION`)

Each upload returns a summary with `created` count and any `failed` rows.

### Regenerating fixture files

The fixtures are already committed. To regenerate them (e.g. after changing the generator):

```bash
cd backend
uv run python tests/fixtures/generate.py
```

---

## Running the backend tests

Tests use **testcontainers** — a real PostgreSQL container is spun up automatically. No running stack needed.

> **Mac-specific:** Docker Desktop on macOS exposes the socket at a non-standard path. Export these two variables before running tests:
>
> ```bash
> export DOCKER_HOST=unix:///Users/$USER/.docker/run/docker.sock
> export TESTCONTAINERS_RYUK_DISABLED=true
> ```

### Fast tests (default — skips the 50k-row scale suite)

```bash
cd backend
DOCKER_HOST=unix:///Users/$USER/.docker/run/docker.sock \
TESTCONTAINERS_RYUK_DISABLED=true \
uv run pytest tests/ -v -m "not slow"
```

### All tests including scale

```bash
cd backend
DOCKER_HOST=unix:///Users/$USER/.docker/run/docker.sock \
TESTCONTAINERS_RYUK_DISABLED=true \
uv run pytest tests/ -v
```

> The scale suite (`-m slow`) loads 50 000 animals and 200 000 events into a real database. It takes several minutes and is excluded from the default run to keep CI feedback short.

### Only scale tests

```bash
cd backend
DOCKER_HOST=unix:///Users/$USER/.docker/run/docker.sock \
TESTCONTAINERS_RYUK_DISABLED=true \
uv run pytest tests/ -v -m slow
```

---

## API reference

### Animals

| Method | Path | Description |
|---|---|---|
| `GET` | `/animals` | Paginated list. Query params: `page`, `limit`, `status`, `lot_id`, `tag_number` |
| `GET` | `/animals/{id}` | Single animal by UUID |
| `POST` | `/animals/bulk` | Bulk create via JSON body or CSV file upload |
| `GET` | `/animals/{id}/history` | Paginated event history for an animal |
| `POST` | `/animals/bulk/events` | Bulk create events via JSON or CSV. Query param: `type` |

### Lots

| Method | Path | Description |
|---|---|---|
| `GET` | `/lots` | Paginated list. Query params: `page`, `limit`, `field_id` |
| `GET` | `/lots/{id}` | Single lot by UUID |
| `GET` | `/lots/{id}/animals` | All active animals currently in a lot |
| `GET` | `/lots/{id}/adg` | Average Daily Gain for a lot. Query params: `from`, `to`, `min_days` |

### Pagination envelope

```json
{
  "data": [...],
  "page": 1,
  "limit": 50,
  "has_next": true
}
```

### CSV column reference

| Upload | Required columns |
|---|---|
| Animals | `tag_number`, `breed`, `category`, `birth_date`, `lot_id`, `occurred_at` |
| WEIGHT events | `tag_number`, `occurred_at`, `weight_kg` |
| VACCINATION events | `tag_number`, `occurred_at`, `vaccine_name` |
| MOVE events | `tag_number`, `occurred_at`, `from_lot_id`, `to_lot_id` |
| DEATH / SALE events | `tag_number`, `occurred_at` |
| RECLASSIFICATION events | `tag_number`, `occurred_at`, `new_category` |

Event CSVs identify animals by `tag_number`. The service resolves all tags to UUIDs in a single query before writing.

---

## Query analysis and known improvement opportunities

### ADG query (`GET /lots/{id}/adg`)

`EXPLAIN ANALYZE` on 50 000 animals / 200 000 WEIGHT events measured **~530 ms** execution time. The plan uses two Hash Joins, each doing a sequential scan of the `events` table (300 000 rows, filtering to 200 000 `WEIGHT` rows):

```
Seq Scan on events  (cost=… rows=168052 …) (actual time=…111ms rows=200000 loops=1)
  Filter: (occurred_at BETWEEN … AND … AND type = 'WEIGHT')
```

The partial index `idx_events_weight_adg (animal_id, occurred_at) WHERE type = 'WEIGHT'` is intentionally not used here: the planner prefers a sequential scan when the result set is a large fraction of the table (~67 %), which is cheaper than 200 000 random index lookups.

**Identified optimisation paths (not implemented):**

1. **Covering index with extracted column.** Add a stored generated column `weight_kg numeric GENERATED ALWAYS AS ((payload->>'weight_kg')::numeric) STORED` and include it in the partial index `(animal_id, occurred_at, weight_kg) WHERE type = 'WEIGHT'`. This enables index-only scans and eliminates the JSONB heap fetch on each row.

2. **`LATERAL` + index-only scan.** Rewrite the CTEs as `CROSS JOIN LATERAL (… ORDER BY occurred_at ASC LIMIT 1)` per animal. With the covering index above, each LATERAL does a single index-only lookup instead of a full scan, reducing cost from O(total WEIGHT events) to O(animals in lot). Without the covering index the LATERAL approach is slower due to random heap fetches (measured: ~1 220 ms vs ~530 ms on a cold buffer pool).

3. **`work_mem` tuning.** The Hash Join spills to 4 batches (`Batches: 4`) because the hash table exceeds the default `work_mem`. Raising it to 32–64 MB for this query would keep the hash in memory and cut the sort + hash cost significantly.

---

