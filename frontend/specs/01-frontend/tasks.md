# Tasks — Animal Traceability (MVP Frontend)

**Date:** 2026-06-09
**Refs:** requirements.md, design.md

Ordered implementation checklist. Each task is a discrete, verifiable step.

---

## Phase 1 — Project setup

- [ ] **1.1** Scaffold project: `npm create vite@latest frontend -- --template react-ts` inside the repo root
- [ ] **1.2** Install dependencies:
  - `react-router-dom`, `@tanstack/react-query`, `axios` (or keep native fetch)
  - `tailwindcss`, `@tailwindcss/vite`, `tailwind-merge`, `clsx`
  - `shadcn/ui` init: `npx shadcn@latest init`
- [ ] **1.3** Install Tabler Icons: `npm install @tabler/icons-react`
- [ ] **1.4** Configure `vite.config.ts`: add proxy `/api → http://localhost:8000`
- [ ] **1.5** Create `.env.example` with `VITE_API_BASE=/api`
- [ ] **1.6** Configure `tailwind.config.ts`: content paths, extend theme with the design tokens from the mockup (primary blue `#2563eb`, sidebar border `#e8eaed`, etc.)
- [ ] **1.7** Add `frontend/` to root `.gitignore` entries for `node_modules/`, `dist/`
- [ ] **1.8** Verify `npm run dev` starts without errors at `http://localhost:5173`

---

## Phase 2 — Base layout

- [ ] **2.1** Create `src/lib/utils.ts`: `cn()` helper (tailwind-merge + clsx)
- [ ] **2.2** Create `src/lib/format.ts`: `formatDate(iso: string): string` (DD/MM/YYYY), `formatDecimal(n: number, places: number): string`
- [ ] **2.3** Install shadcn/ui components needed across the app: `button`, `badge`, `input`, `select`, `table`, `skeleton`, `separator`
- [ ] **2.4** Create `src/components/layout/Sidebar.tsx`: logo, nav items with active state driven by `useLocation()`, static structure matching the design (Trazabilidad section + Gestión section)
- [ ] **2.5** Create `src/components/layout/Topbar.tsx`: accepts `title` and `actions` (React node slot) as props
- [ ] **2.6** Create `src/components/layout/AppLayout.tsx`: fixed sidebar + scrollable main area, renders `<Outlet />` for child routes
- [ ] **2.7** Create `src/App.tsx`: `RouterProvider` with `createBrowserRouter`, define all 4 routes under `AppLayout`, redirect `/` → `/history`
- [ ] **2.8** Create `src/main.tsx`: `QueryClientProvider` wrapping `RouterProvider`, `ReactDOM.createRoot`
- [ ] **2.9** Verify navigation between the 4 routes works and the active sidebar item updates correctly

---

## Phase 3 — Types and API layer

- [ ] **3.1** Create `src/types/event.ts`: `EventType` union, `Event` interface, `PaginatedResponse<T>` generic
- [ ] **3.2** Create `src/types/animal.ts`: `AnimalStatus`, `Breed`, `AnimalCategory` unions, `Animal` interface
- [ ] **3.3** Create `src/types/lot.ts`: `Lot`, `LotAnimalsResponse`, `AdgResponse`, `BulkResult` interfaces
- [ ] **3.4** Create `src/api/client.ts`: base fetch helper with `VITE_API_BASE`, throws on non-2xx with parsed error body
- [ ] **3.5** Create `src/api/animals.ts`: `getAnimals(params?: { page?, limit?, status?, lot_id?, tag_number? })`, `getAnimalHistory(id, page, limit)`, `bulkCreateAnimals(file: File)`, `bulkCreateEvents(type: EventType, file: File)`
- [ ] **3.6** Create `src/api/lots.ts`: `getLots()`, `getLotAnimals(lotId)`, `getLotAdg(lotId, params)`
- [ ] **3.7** Create shared UI components: `<ErrorMessage />` (displays API error), `<PageSkeleton />` (generic loading placeholder), `<StatCard />` (label + value + optional sub)

---

## Phase 4 — Historial animal (US-FE-01)

- [ ] **4.1** Create `src/hooks/useAnimalHistory.ts`: TanStack Query hook wrapping `getAnimalHistory`, key `['animal-history', animalId, page, eventType]`
- [ ] **4.2** Create `src/hooks/useAnimals.ts`: TanStack Query hook wrapping `getAnimals`, key `['animals', tag_number]`, enabled only when `tag_number.length >= 2`
- [ ] **4.3** Create `src/pages/AnimalHistory.tsx`:
  - Filter row: tag search input (debounced 300ms, dropdown of matching animals) + event type select
  - Timeline component with colored dots, event type badges, date, payload summary
  - Pagination controls
  - Empty state (no animal selected) and error states
  - No animal header card
- [ ] **4.4** Wire animal selection to URL search param `?animal=<uuid>` so the selected animal survives a page refresh
- [ ] **4.5** Verify: selecting an animal loads its history, filter by type works, pagination advances correctly

---

## Phase 5 — Estado de lote (US-FE-02)

- [ ] **5.1** Create `src/hooks/useLots.ts`: TanStack Query hook wrapping `getLots()`, key `['lots']`
- [ ] **5.2** Create `src/hooks/useLotAnimals.ts`: TanStack Query hook wrapping `getLotAnimals(lotId)`, key `['lot-animals', lotId]`
- [ ] **5.3** Create `src/pages/LotStatus.tsx`:
  - Tab bar populated from `useLots()` — active tab driven by URL search param `?lot=<uuid>`
  - Two stat cards (active animal count, category breakdown — computed client-side)
  - Animal table (tag number, breed, category, status, birth date) with client-side search input
  - Empty and error states
- [ ] **5.4** Verify: switching tabs loads the correct lot's animals, client-side search filters the table without a new network request

---

## Phase 6 — ADG (US-FE-03)

- [ ] **6.1** Create `src/hooks/useLotAdg.ts`: TanStack Query hook wrapping `getLotAdg(lotId, params)`, key `['lot-adg', lotId, from, to, minDays]`
- [ ] **6.2** Create `src/pages/Adg.tsx`:
  - Filter row: lot select (All + each lot from `useLots()`), date from/to inputs, min days input
  - Filters sync to URL search params
  - Summary stat cards (lots analyzed, total animals, global avg ADG, best lot)
  - ADG card per lot: name, period, avg ADG / animal count, relative performance bar (color: blue = best, green = ≥70%, orange = <70%; bar width = lot.avg / max(all_lots.avg) * 100)
  - "Sin datos suficientes" state when `animals_count = 0`
- [ ] **6.3** Verify: changing filters triggers new queries, "all lots" mode merges results from multiple calls, URL params persist on refresh

---

## Phase 7 — Carga de datos (US-FE-04 / US-FE-05)

- [ ] **7.1** Create `src/components/DropZone.tsx`: accepts `onFile: (file: File) => void`, shows file name after selection, supports drag-and-drop and click-to-browse
- [ ] **7.2** Create `src/components/BulkResultCard.tsx`: displays `created` (green), `failed` (red), expandable list of failed rows
- [ ] **7.3** Create `src/pages/Upload.tsx`:
  - Two-panel grid layout matching design.md
  - Left panel (animals): `DropZone`, column hint `tag_number,breed,category,birth_date,lot_id,occurred_at`, submit button (disabled + spinner while loading)
  - Right panel (events): event type chip selector (WEIGHT/MOVE/VACCINATION/DEATH/SALE/RECLASSIFICATION/BIRTH), `DropZone` with dynamic column hint per type, submit button
  - Both buttons vertically aligned at card bottom via flex-column + margin-top:auto
  - `BulkResultCard` below both panels, updated after each submission
  - Uses `useMutation` from TanStack Query; sends `multipart/form-data` with field name `file`
- [ ] **7.4** Verify: uploading a valid CSV shows the correct `created` count; uploading a CSV with intentional errors shows failed row details

---

## Phase 8 — Backend additions (prerequisite for phases 4–6)

`GET /animals?tag_number=XXX` is already implemented. The only missing endpoint is `GET /lots`.

- [ ] **8.1** Add `GET /lots` router handler to `backend/app/routers/lots.py`:
  - Calls `LotService.get_lots(page, limit, field_id)` — **service already exists**
  - Returns `PaginatedResponse[LotResponse]` — **both schemas already exist**
  - Query params: `page=1`, `limit=50`, `field_id` (optional)
- [ ] **8.2** Verify `GET /lots` returns correct data with the seeder loaded

---

## Phase 9 — Integration and polish

- [ ] **9.1** End-to-end smoke test with the backend running and seeder data loaded:
  - Navigate to each of the 4 pages
  - Verify data loads correctly from the real API (not mock)
  - Verify error states appear correctly when the backend is stopped
- [ ] **9.2** Verify all URL search params persist on page refresh (lot selection, animal selection, ADG filters)
- [ ] **9.3** Check loading skeletons appear on slow connections (throttle in DevTools to Slow 3G)
- [ ] **9.4** Verify keyboard navigation works on all interactive elements (tab through sidebar, filters, table)
- [ ] **9.5** Add `frontend/` run instructions to the root `README.md`
