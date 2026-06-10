# Design — Animal Traceability (MVP Frontend)

**Date:** 2026-06-09
**Scope:** MVP frontend. Stack: React 18, Vite, TypeScript, React Router v6, TanStack Query v5, Tailwind CSS, shadcn/ui.

---

## Architecture

```
Browser
  ↓
React Router v6     (src/App.tsx)           — client-side routing
  ↓
Page components     (src/pages/*.tsx)        — route-level components
  ↓
Custom hooks        (src/hooks/*.ts)         — TanStack Query wrappers
  ↓
API layer           (src/api/*.ts)           — typed fetch functions
  ↓
Backend (FastAPI)   http://localhost:8000    — via Vite proxy /api → :8000
```

---

## Directory structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          # base fetch helper, base URL from env
│   │   ├── animals.ts         # getAnimals, getAnimalHistory, bulkCreateAnimals, bulkCreateEvents
│   │   └── lots.ts            # getLots, getLotAnimals, getLotAdg
│   ├── components/
│   │   ├── ui/                # shadcn/ui generated components (Button, Select, Table, Badge…)
│   │   └── layout/
│   │       ├── AppLayout.tsx  # sidebar + topbar shell
│   │       ├── Sidebar.tsx    # nav items, active state
│   │       └── Topbar.tsx     # title + action buttons slot
│   ├── pages/
│   │   ├── AnimalHistory.tsx  # US-FE-01
│   │   ├── LotStatus.tsx      # US-FE-02
│   │   ├── Adg.tsx            # US-FE-03
│   │   └── Upload.tsx         # US-FE-04 / US-FE-05
│   ├── hooks/
│   │   ├── useAnimals.ts
│   │   ├── useAnimalHistory.ts
│   │   ├── useLots.ts
│   │   ├── useLotAnimals.ts
│   │   └── useLotAdg.ts
│   ├── types/
│   │   ├── animal.ts          # Animal, AnimalStatus, Breed, AnimalCategory
│   │   ├── event.ts           # Event, EventType, payload shapes
│   │   └── lot.ts             # Lot, LotAnimalsResponse, AdgResponse
│   ├── lib/
│   │   ├── utils.ts           # cn() helper (shadcn/ui)
│   │   └── format.ts          # formatDate, formatDecimal
│   ├── App.tsx                # RouterProvider + route definitions
│   └── main.tsx               # ReactDOM.createRoot, QueryClientProvider
├── public/
├── index.html
├── vite.config.ts             # proxy /api → http://localhost:8000
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── .env.example
```

---

## Routes

| Path | Component | Description |
|---|---|---|
| `/` | redirect | → `/history` |
| `/history` | `AnimalHistory` | Historial del animal (US-04) |
| `/lot` | `LotStatus` | Estado del lote (US-05) |
| `/adg` | `Adg` | Ganancia diaria de peso (US-06) |
| `/upload` | `Upload` | Carga masiva de animales y eventos (US-01/02/03) |

---

## Dev setup

### Vite proxy

```ts
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

All API calls use the `/api` prefix in development. In the API layer, `client.ts` sets `BASE_URL = '/api'`. The proxy strips the prefix before forwarding to FastAPI, so no CORS configuration is needed on the backend during development.

### Environment variables

```bash
# .env.example — no secrets in MVP
VITE_API_BASE=/api
```

### Local run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The backend must be running on `:8000` (via `docker compose up` or `uvicorn app.main:app --port 8000`).

---

## API layer

### `src/api/client.ts`

Thin wrapper around `fetch`. Reads `VITE_API_BASE` from env, throws on non-2xx responses with the parsed error body.

```ts
const BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw await res.json()
  return res.json()
}

export const api = { get, post, postForm }
```

### `src/api/animals.ts`

```ts
// GET /animals?tag_number=XXX  (returns matching animal(s) by exact or partial tag)
getAnimals(params?: { page?: number; limit?: number; status?: AnimalStatus; lot_id?: string; tag_number?: string }): Promise<PaginatedResponse<Animal>>
// GET /animals/{id}/history?page=&limit=
getAnimalHistory(id: string, page: number, limit: number): Promise<PaginatedResponse<Event>>
// POST /animals/bulk — multipart/form-data, field "file" (CSV)
bulkCreateAnimals(file: File): Promise<BulkResult>
// POST /animals/bulk/events?type=TYPE — multipart/form-data, field "file" (CSV)
bulkCreateEvents(type: EventType, file: File): Promise<BulkResult>
```

### `src/api/lots.ts`

```ts
// GET /lots?page=&limit=
getLots(params?: { page?: number; limit?: number }): Promise<PaginatedResponse<Lot>>
// GET /lots/{id}/animals
getLotAnimals(lotId: string): Promise<LotAnimalsResponse>
// GET /lots/{id}/adg?from=&to=&min_days=
getLotAdg(lotId: string, params: AdgParams): Promise<AdgResponse>
```

---

## Pages

### AnimalHistory — US-FE-01

**Endpoint:** `GET /animals/{id}/history?page=&limit=`

**Layout:**
- Filter row: tag search input (debounced, shows matching animals in a dropdown) + event type select
- Timeline: paginated list of events (colored dot + event type badge + date + payload summary)
- No animal header card — event payloads contain all relevant data

**State:**
- Selected animal ID from URL search param (`?animal=<uuid>`)
- Active event type filter (client-side, applied over the loaded page)
- Current page (TanStack Query handles caching per `[animal_id, page]` key)

**TanStack Query key:** `['animal-history', animalId, page, eventType]`

---

### LotStatus — US-FE-02

**Endpoint:** `GET /lots/{id}/animals`

**Layout:**
- Tab bar: one tab per lot (populated from `GET /lots`)
- Stat cards: active animal count, category breakdown (computed client-side from the animals list)
- Table: tag number, breed, category, status badge, birth date
- Search input filters table client-side

**Note:** `AnimalResponse` does not include `weight_last` or lot `capacity`. The "average weight" and "occupancy %" stat cards from the mockup are **not implementable** with the current backend response and are excluded. They can be added in v2 if the backend adds these fields.

**State:**
- Active lot ID from URL search param (`?lot=<uuid>`)
- Client-side search string

**TanStack Query keys:**
- `['lots']` for the lot list
- `['lot-animals', lotId]` for the animal table

---

### Adg — US-FE-03

**Endpoint:** `GET /lots/{id}/adg?from=&to=&min_days=`

**Layout:**
- Filter row: lot select (all lots or one), date from, date to, min days input
- Summary stat cards: lots analyzed, total animals, global avg ADG, best lot name
- ADG card per lot: lot name, period, avg ADG (kg/day), animal count, relative performance bar

**Note:** `AdgResponse` only includes `avg_adg_kg_day` — there is no `max_adg` field. The maximum ADG shown in the mockup is **not available** from the backend and is excluded. The relative performance bar is computed client-side as `lot.avg / max(all_lots.avg) * 100`.

**State:**
- All filters in URL search params (`?lot=&from=&to=&min_days=`)
- When lot = "all": one `useLotAdg` call per lot, results merged client-side
- When lot = specific: single `useLotAdg` call

**TanStack Query key:** `['lot-adg', lotId, from, to, minDays]`

---

### Upload — US-FE-04 / US-FE-05

**Endpoints:**
- `POST /animals/bulk` — `multipart/form-data` with field `file` (CSV)
- `POST /animals/bulk/events?type=<TYPE>` — `multipart/form-data` with field `file` (CSV)

**Layout:**
- Two-panel grid (1fr 1fr):
  - **Left — Registrar animales:** drag-drop CSV zone, submit button. Column hint: `tag_number, breed, category, birth_date, lot_id, occurred_at`.
  - **Right — Registrar eventos:** event type chip selector (WEIGHT / MOVE / VACCINATION / DEATH / SALE / RECLASSIFICATION / BIRTH), drag-drop CSV zone, submit button. Column hint updates per type (see requirements.md US-FE-05).
- Both submit buttons are vertically aligned at the bottom of their cards.
- Result card below both panels: `created` count in green, `failed` count in red, expandable list of failed rows with row number and reason.

**Behavior:**
- Accepts CSV files via drag-and-drop or file input.
- On submit, sends `multipart/form-data` (field name `file`) to the corresponding endpoint.
- CSV events use `tag_number` — the backend resolves the animal UUID internally; no UUID lookup needed from the frontend.
- While uploading: button shows spinner, disabled.
- On success/error: result card updates below.

**TanStack Query:** uses `useMutation` for both upload actions. No query caching needed.

---

## TypeScript types

### `src/types/event.ts`

```ts
export type EventType =
  | 'BIRTH' | 'MOVE' | 'WEIGHT' | 'VACCINATION'
  | 'DEATH' | 'SALE' | 'RECLASSIFICATION'

export interface Event {
  id: string
  animal_id: string           // included in EventResponse
  type: EventType
  occurred_at: string         // ISO 8601 datetime
  payload: Record<string, string>
}

export interface PaginatedResponse<T> {
  data: T[]
  page: number
  limit: number
  has_next: boolean
}
```

### `src/types/animal.ts`

```ts
// Matches backend app/models/enums.py exactly
export type AnimalStatus = 'ACTIVE' | 'DEAD' | 'SOLD'
export type Breed = 'ANGUS' | 'HEREFORD' | 'BRAHMAN' | 'LIMOUSIN' | 'SHORTHORN' | 'CRIOLLO'
export type AnimalCategory = 'CALF' | 'STEER' | 'COW' | 'BULL' | 'HEIFER'

// Matches AnimalResponse schema
export interface Animal {
  id: string
  tag_number: string
  breed: Breed
  category: AnimalCategory
  status: AnimalStatus
  birth_date: string | null   // date string "YYYY-MM-DD"
  current_lot_id: string | null
}

// Matches AnimalBulkCreateResponse / EventBulkCreateResponse
export interface BulkResult {
  created: number
  failed: Record<string, unknown>[]   // backend returns list[dict] — shape varies by error type
}
```

### `src/types/lot.ts`

```ts
// Matches LotResponse schema
export interface Lot {
  id: string
  name: string
  field_id: string
}

// Matches GET /lots/{id}/animals response: { "animals": [...] }
export interface LotAnimalsResponse {
  animals: Animal[]
}

// Matches AdgResponse schema — avg_adg_kg_day is Decimal|None serialized as number|null
export interface AdgResponse {
  lot_id: string
  lot_name: string
  period: { from: string; to: string }
  animals_count: number
  avg_adg_kg_day: number | null
}
```

---

## Missing backend endpoints

`GET /animals?tag_number=XXX` is **already implemented** — use it to find an animal by tag and retrieve its `id` for subsequent `GET /animals/{id}/history` calls.

The only missing router endpoint is `GET /lots`:

| Endpoint | Router file | Service method | Missing piece |
|---|---|---|---|
| `GET /lots` | `routers/lots.py` | `LotService.get_lots(page, limit, field_id)` | Add router handler only |

`GET /lots` response shape (using existing `LotResponse` schema + `PaginatedResponse`):
```json
{ "data": [{ "id": "uuid", "name": "Potrero Norte", "field_id": "uuid" }], "page": 1, "limit": 50, "has_next": false }
```

---

## Non-functional

- **No auth:** MVP has no login screen or token handling. All endpoints are open.
- **Error boundaries:** each page wraps its TanStack Query in a simple error state (`<ErrorMessage />` component) rather than crashing the whole app.
- **Loading states:** every data-fetching component shows a skeleton or spinner while `isLoading` is true.
- **No i18n:** UI labels are in Spanish throughout, matching the prototype.
