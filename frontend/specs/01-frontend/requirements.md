# Requirements — Animal Traceability (MVP Frontend)

**Date:** 2026-06-09
**Scope:** MVP frontend in React + Vite + TypeScript. Consumes the backend API. Design specified in design.md.

---

## Context

The backend exposes a REST API for individual animal traceability. This frontend is the web interface that livestock producers use to consult and load data. There is no login screen in this MVP — single admin user assumed.

---

## Users and roles

**MVP scope:** single admin user. No auth, no RBAC.

The primary actor is the **livestock producer** who operates through the web application. Operations are either consulted in real time or loaded in bulk from spreadsheets exported from external tools.

---

## User stories

### US-FE-01 — Animal history

> As a producer or veterinarian, I want to search for an animal by its ear tag and see the complete timeline of its events, to reconstruct its trajectory.

**Acceptance criteria:**
- The user can search for an animal by tag number. The search calls `GET /animals?tag_number=` and shows matching results as a dropdown or list.
- Selecting an animal loads its full event timeline via `GET /animals/{id}/history`.
- The timeline is paginated and ordered from most recent to oldest.
- Each timeline item shows: event type badge (with color by type), date, and payload summary (e.g. `weight_kg`, `vaccine_name`, `new_category`, `to_lot_id`).
- The user can filter the timeline by event type via a select input (client-side filter over the loaded page).
- If no animal is selected, the page shows an empty state with a prompt to search.
- If the animal has no events, the timeline shows an empty state message.

---

### US-FE-02 — Lot status

> As a producer, I want to see which animals are currently in each lot, to know the composition and occupancy of my fields.

**Acceptance criteria:**
- A tab bar lists all available lots (populated from `GET /lots`).
- Selecting a tab calls `GET /lots/{id}/animals` and renders a table with: tag number, breed, category, status badge, birth date.
- Two stat cards summarize: active animal count, and category breakdown (computed client-side from the animals list).
- Note: average weight and occupancy % require fields not present in the current backend response (`weight_last`, `capacity`) and are excluded from MVP.
- The user can filter the table client-side by typing a tag number or breed in a search input.
- If the lot has no active animals, the table shows an empty state.

---

### US-FE-03 — ADG (Average Daily Gain)

> As a producer, I want to know the average daily weight gain of the animals in a lot during a specific period, to compare performance between pastures.

**Acceptance criteria:**
- Filter row allows selecting: one lot or all lots, date range (from / to), and minimum days between weighings (`min_days`).
- Filters are reflected in URL search params so they can be bookmarked or shared.
- For each lot in scope, the page shows an ADG card with: lot name, period, average ADG (kg/day), animal count, and a relative performance bar.
- Note: maximum ADG is not returned by the backend (`AdgResponse` only has `avg_adg_kg_day`) and is excluded from MVP.
- Summary stat cards at the top show: lots analyzed, total animals, global average ADG, best performing lot.
- When `animals_count = 0` for a lot, the card explicitly states "sin datos suficientes".
- When "all lots" is selected, one `GET /lots/{id}/adg` call is made per lot and results are merged client-side.

---

### US-FE-04 — Bulk animal upload

> As a producer, I want to upload a CSV or JSON file with hundreds of animals at once, to register a newly acquired herd without entering them one by one.

**Acceptance criteria:**
- The upload form accepts a CSV file via drag-and-drop or file input.
- On submit, the file is sent to `POST /animals/bulk` as `multipart/form-data` (field name: `file`).
- While the request is in progress, the submit button is disabled and shows a spinner.
- On completion, a result card shows: `created` count (green) and `failed` count (red). If there are failures, they are listed with row number and reason.
- The CSV column hint is shown below the drop zone: `tag_number, breed, category, birth_date, lot_id, occurred_at` (`occurred_at` is optional).

---

### US-FE-05 — Bulk event upload

> As a producer, I want to upload a CSV with weight measurements, vaccinations, movements, or other events for a group of animals, to record field operations efficiently.

**Acceptance criteria:**
- The user first selects the event type via a chip selector: WEIGHT, MOVE, VACCINATION, DEATH, SALE, RECLASSIFICATION, BIRTH.
- The CSV column hint below the drop zone updates dynamically when the type chip changes. Required columns per type:
  - `WEIGHT`: `tag_number, occurred_at, weight_kg`
  - `MOVE`: `tag_number, occurred_at, from_lot_id, to_lot_id`
  - `VACCINATION`: `tag_number, occurred_at, vaccine_name`
  - `RECLASSIFICATION`: `tag_number, occurred_at, new_category`
  - `DEATH` / `SALE` / `BIRTH`: `tag_number, occurred_at`
- Note: CSV events use `tag_number` — the backend resolves the animal UUID internally.
- On submit, the file is sent to `POST /animals/bulk/events?type=<TYPE>` as `multipart/form-data` (field name: `file`).
- While the request is in progress, the submit button is disabled and shows a spinner.
- On completion, same result card as US-FE-04: `created` count, `failed` count, and failure details.

---

## Non-functional requirements

### Performance
- Page transitions are instant (client-side routing, no full reload).
- TanStack Query caches responses — navigating back to a previously loaded lot or animal does not trigger a new network request unless the cache is stale.

### Resilience
- Each page wraps its data-fetching in an error boundary. A network error or 4xx/5xx response shows a localized error message without crashing the entire app.
- While data is loading, every data-dependent section shows a skeleton or spinner.

### Developer experience
- Vite proxy eliminates CORS issues during local development — no backend changes needed.
- TypeScript types in `src/types/` match backend schemas exactly. No `any` types in the API layer.

### Accessibility
- All interactive elements are keyboard-accessible (shadcn/ui components handle this by default).
- Status badges use both color and text — not color alone.

---

## Backend additions required

These router endpoints do not exist yet. The service and repository methods are already implemented — only a router handler (and one repo filter) need to be added.

| Endpoint | Needed by | Effort |
|---|---|---|
| `GET /lots` | US-FE-02 tab bar, US-FE-03 lot selector, US-FE-04 lot selector | Router handler only — `LotService.get_lots` and `LotRepository.get_paginated` already exist |

---

## Out of scope (MVP)

| Excluded | Reason |
|---|---|
| Authentication / login screen | Single admin user assumed |
| Creating / editing / deleting lots or fields via UI | Backend has no write endpoints for these |
| Real-time updates / WebSocket | Not needed at this scale |
| Charts / graphs | Plain stat cards and bars are sufficient for the MVP |
| Mobile responsive layout | Internal tool, desktop-first |
| Dark mode | Not in scope |
| Internationalization | Spanish-only UI |
