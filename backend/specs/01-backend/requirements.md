# Requirements — Animal Traceability (MVP)

**Date:** 2026-06-09
**Scope:** MVP backend in ~10 hours. Frontend specified in separate specs.

---

## Problem

The platform currently operates on a lot-centric model: events are recorded against the lot, not the individual animal. There is no individual animal identity.

The goal is to evolve toward 1:1 traceability: knowing what each animal is, where it is, what happened to it, and being able to reconstruct its complete history.

---

## Users and roles

**MVP scope:** single admin user. No auth, no RBAC, no multi-tenancy.

The primary actor is the **livestock producer** who operates through a web application (not implemented in this MVP). Operations are assisted by field staff or entered in bulk from spreadsheets.

---

## User stories

### US-01 — Bulk animal registration

> As a producer, I want to register hundreds of animals at once (for example, when receiving a purchased herd) without having to enter them one by one.

**Acceptance criteria:**
- The endpoint accepts JSON or CSV via `multipart/form-data`.
- Each record includes `tag_number`, `breed`, `category`, `birth_date`, `lot_id` and `occurred_at` — allows creating animals in different lots in a single operation.
- All animals are inserted in a single SQL operation per batch (UNNEST), not N separate queries.
- CSV is processed in streaming with batches of 1000 rows.
- If a `lot_id` is invalid, the system reports which records failed (with row number) without aborting the valid ones.
- Each created animal has an internal UUID as a permanent identity (the ear tag `tag_number` may change).
- A `BIRTH` event is automatically registered for each created animal.
- An `animal_lot_period` is opened for each animal in the destination lot.
- `occurred_at` is optional — if not provided, the system uses `NOW()`. When provided, it allows importing historical data with the actual lot entry date.

---

### US-02 — Bulk animal movement between lots

> As a producer, I want to move a group of animals from one lot to another in a single operation (for example, when changing pasture after weaning).

**Acceptance criteria:**
- Movement is registered via `POST /animals/bulk/events` with `type: "MOVE"` and `payload: { from_lot_id, to_lot_id }` — no separate endpoint.
- The entire operation occurs in a single transaction: if anything fails, nothing is applied.
- A `MOVE` event is generated for each animal.
- The `current_lot_id` projection on `animals` is updated.
- The active `animal_lot_period` is closed (`exited_at = occurred_at`) and a new one is opened in the destination lot.
- The system serializes concurrent movements on the same animals (SELECT FOR UPDATE) to prevent double open periods.
- If k of N animals do not exist or are not in `from_lot_id`, the system reports which ones failed without aborting the valid ones.
- The entire operation uses 5 SQL queries with UNNEST/ANY, not N queries.

---

### US-03 — Bulk event registration

> As a producer, I want to register events (weighings, vaccinations, deaths, sales, movements) on a group of animals at once, including from a CSV file with hundreds of thousands of rows.

**Acceptance criteria:**
- The endpoint accepts both JSON (small payload) and CSV via `multipart/form-data` (hundreds of thousands of rows).
- Valid types: `BIRTH`, `MOVE`, `DEATH`, `SALE`, `RECLASSIFICATION`, `WEIGHT`, `VACCINATION`.
- Required payload varies by type (see payload table in design). The system validates the presence of required fields.
- For `DEATH` or `SALE` events, the `status` projection on `animals` is updated to `DEAD` or `SOLD`.
- For `RECLASSIFICATION` events, the `category` projection on `animals` is updated.
- `occurred_at` is required (no hardcoded `NOW()`).
- CSV is processed in streaming (never fully loaded into memory) in batches of 1000 rows.
- The response is synchronous and includes `created` (total processed) and `failed` (rows with errors, with row number and reason).
- Rows with errors do not abort processing of the rest of the file.

---

### US-04 — Complete animal history

> As a producer or veterinarian, I want to see all events that occurred to a specific animal, in reverse chronological order (most recent first), to reconstruct its trajectory.

**Acceptance criteria:**
- The endpoint returns all animal events ordered by `occurred_at` descending.
- Paginated response: `page` (default 1) and `limit` (default 50) parameters.
- The response includes `data`, `page`, `limit`, and `has_next`.
- Response SLA is < 50ms with correct indexes.
- If the animal does not exist or is deleted, returns 404.

---

### US-05 — Current lot status

> As a producer, I want to see which animals are currently in a lot (active, not sold or dead) with their basic information.

**Acceptance criteria:**
- The endpoint returns animals with `status = 'ACTIVE'` whose `current_lot_id` matches the lot.
- Includes per animal: `id`, `tag_number`, `breed`, `category`, `status`, `birth_date`.
- If the lot does not exist or is deleted, returns 404.

---

### US-06 — ADG by historical lot (star feature)

> As a producer, I want to know the average daily weight gain of the animals in a lot during a period, to compare performance between pastures and identify operational differences (grass, water, density, health).

**Acceptance criteria:**
- The endpoint accepts `lot_id`, `from` (start date), `to` (end date) and `min_days` (minimum days between first and last weighing).
- Only animals that were in that specific lot during the measurement period are included.
- Only weighings recorded while the animal was in that lot are used (not weighings from other lots).
- The `min_days` parameter filters animals with insufficient measurement periods for statistically reliable data.
- The response includes: `lot_id`, `lot_name`, `period`, `animals_count`, `avg_adg_kg_day`.
- Weights are calculated using `NUMERIC` / `Decimal` (never `float`) to avoid accumulated rounding errors.
- If there are no animals with sufficient data in the period, `animals_count = 0` and `avg_adg_kg_day = null`.
- If the lot does not exist, returns 404.

---

## Non-functional requirements

### Performance
- `GET /animals/{id}/history`: < 50ms with correct indexes.
- `GET /lots/{id}/adg`: < 100ms for a lot of 1,000 animals with correct indexes.
- All bulk operations use UNNEST/ANY — never N separate queries in a loop.

### Data correctness
- Weights (`weight_kg`) are stored as `NUMERIC` in PostgreSQL and `Decimal` in Python. Use of `float` is forbidden for weight fields.
- Events are immutable: they have no `updated_at` or `deleted`. Recording an incorrect event is corrected with a new compensating event, not by editing the original.
- Projections (`status`, `category`, `current_lot_id`) are kept consistent with events within the same transaction.

### Consistency
- The bulk move operation guarantees that each animal has exactly one `animal_lot_period` with `exited_at IS NULL` at all times (enforced by a partial UNIQUE index in DB and SELECT FOR UPDATE in the transaction).
- The 5 SQL operations of the bulk move occur in an atomic transaction.

### Observability
- Structured logging with level configurable via environment variable.

### Synthetic dataset
- The seeder generates historical data distributed over time with `occurred_at` in past dates.
- After the seeder completes, `ANALYZE events` and `ANALYZE animal_lot_periods` are executed so the query planner has correct statistics.

---

## Out of scope (MVP)

| Excluded | Reason |
|---|---|
| Frontend | Specified in separate frontend specs. |
| Auth / RBAC / multi-tenancy | Single admin user assumed. |
| `events` table partitioning | Designed for v2 without schema changes. Partial indexes mitigate the impact in MVP. |
| `animal_period_summaries` | Over-engineering for this scope. Documented for v2. |
| `animal_tags` (ear tag history) | Not blocking for the star feature. Schema designed and documented to incorporate without structural changes. |
| Microservices, Kafka, CQRS, event sourcing | Unnecessary for a well-built monolith at this scope. |
| Species polymorphism | Not implemented in this MVP. |
