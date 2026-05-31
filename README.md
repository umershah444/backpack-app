# Backpack — Job Costing Prototype

Pre-interview task for the **KTP Associate** role (McCann / University of Suffolk, Ref: 00000).

A prototype that lets an **Operative** record the details of a completed job
(time on site, vehicles, plant/tools, materials) and produces a **job cost**
for the **QS** to review.

| | |
|---|---|
| **Live app** | _<paste your deployed frontend URL here>_ |
| **API docs** | _<paste your deployed API URL>/docs_ |
| **Stack** | React (Vite) · FastAPI (Python) · SQLite/SQLAlchemy · Docker · GitHub Actions · Render |

---

## Run locally

### Backend (Python)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API at http://localhost:8000  ·  interactive docs at /docs
pytest -v            # run the test suite (6 tests)
```

### Frontend (React)
```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_URL to your backend
npm run dev                   # http://localhost:5173
```

### Or run both with Docker
```bash
docker compose up --build
# frontend → http://localhost:3000   backend → http://localhost:8000
```

---

## What it does

The Operative fills one screen. The app computes:

```
total = labour + vehicles + plant + materials
labour   = hours_on_site × labour_rate
vehicles = Σ (vehicle_day_rate × days)
plant    = Σ (plant_day_rate × days)
```

Reference rates are served by the API (`GET /rates`) so they are configurable
in one place. The same formula runs client-side for a live estimate and
server-side as the authoritative figure stored for the QS.

## API endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | health check |
| GET | `/rates` | reference cost rates |
| POST | `/jobs` | submit a job, returns cost breakdown |
| GET | `/jobs` | list submitted jobs (QS) |
| GET | `/jobs/{id}` | single job |

## Repository layout
```
backend/      FastAPI app, costing logic, tests, Dockerfile
frontend/     React job-entry screen (Vite), Dockerfile
.github/      CI pipeline (tests + build on every push)
render.yaml   Render blueprint (backend web service + frontend static site)
```

## Deployment (Render)
Deployment is on [Render](https://render.com) via the `render.yaml` blueprint:

- **backend-api** — Python web service (`uvicorn main:app --host 0.0.0.0 --port $PORT`)
- **backpack-frontend** — static site built from `frontend/` (`npm run build` → `dist/`)

Render auto-deploys on every push to `main`. After the first deploy, set these
environment variables in the Render dashboard:

- on the backend: `ALLOWED_ORIGINS` = your frontend URL
- on the frontend: `VITE_API_URL` = your backend URL
