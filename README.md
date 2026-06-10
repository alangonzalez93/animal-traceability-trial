# animal-traceability-trial
Livestock traceability system with bulk operations and daily weight gain (ADPV) analytics. FastAPI + PostgreSQL + React.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/alangonzalez93/animal-traceability-trial
cd animal-traceability-trial
```

### 2. Create the environment file

```bash
cp .env.example .env
```

The defaults work out of the box — no changes needed.

---

## Running the project

### Start all services (backend and frontend)

```bash
docker compose up --build
```

### Seed field and lots

In a second terminal (with services running):

```bash
DATABASE_URL=postgresql+asyncpg://traceability:traceability@localhost:5432/animal_traceability uv run python -m app.scripts.seed
```

## Go to web

http://localhost:5173/adg

