# IPO Copilot AI — Quick Start

## Prerequisites
- Docker Desktop (Windows): https://www.docker.com/products/docker-desktop/
- Git
- An OpenAI API key (or compatible endpoint)

---

## 1. Clone & Configure

```bash
git clone <your-repo>
cd "SEBI HACKATHON"
```

Copy and edit the environment file:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

---

## 2. Start All Services (One Command)

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5432`
- **FastAPI backend** on port `8000`
- **React frontend** on port `3000`

> First run takes ~3–5 minutes to build images and install npm packages.

---

## 3. Load Demo Data

After services are healthy, seed the demo database:
```bash
docker compose exec backend python -m app.seed
```

Demo credentials:
- **Email:** `demo@ipocolpilot.ai`
- **Password:** `Demo@1234`

---

## 4. Open the App

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Redoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

---

## 5. Useful Commands

```bash
# View live logs
docker compose logs -f

# Restart just backend (after code changes)
docker compose restart backend

# Run database migrations
docker compose exec backend alembic upgrade head

# Re-seed demo data
docker compose exec backend python -m app.seed

# Stop everything
docker compose down

# Stop + remove volumes (full reset)
docker compose down -v
```

---

## Architecture

```
SEBI HACKATHON/
├── docker-compose.yml      # Orchestrates all 3 services
├── backend/                # FastAPI + LangChain AI pipeline
│   ├── app/
│   │   ├── main.py         # FastAPI entry point
│   │   ├── ai/             # LLM, RAG, Compliance Engine, Copilot
│   │   ├── routers/        # REST API routes
│   │   ├── services/       # Business logic
│   │   ├── models/         # SQLAlchemy ORM models
│   │   └── schemas/        # Pydantic request/response schemas
│   └── requirements.txt
└── frontend/               # React + Vite + TanStack Query
    └── src/
        ├── pages/          # 12 workflow pages
        ├── components/     # Reusable UI components
        ├── api/            # TanStack Query hooks
        └── store/          # Zustand state (auth + workspace)
```

---

## Workflow

1. **Login / Register** → `/login`
2. **Company Onboarding** → `/app/onboarding`
3. **IPO Workspace** → `/app/workspace/:id`
4. **Document Upload** → `/app/upload/:id`
5. **AI Validation** → `/app/validation/:id`
6. **SEBI Compliance** → `/app/compliance/:id`
7. **AI Copilot** → `/app/copilot/:id`
8. **Draft Review** → `/app/draft/:id`
9. **Human Review** → `/app/human-review/:id`
10. **Version Tracking** → `/app/versions/:id`
11. **Readiness Dashboard** → `/app/dashboard/:id`
12. **Export** → `/app/export/:id`
