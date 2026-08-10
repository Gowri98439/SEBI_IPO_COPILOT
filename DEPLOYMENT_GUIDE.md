# Deployment Guide
# IPO Copilot AI — Enterprise Platform v2.0.0

---

## Architecture Overview

```
                    ┌─────────────────┐
                    │   nginx (443)   │
                    │  TLS Termination │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────┴───────┐          ┌──────────┴─────┐
     │  Frontend      │          │   Backend       │
     │  nginx (80)    │          │   FastAPI (8000)│
     │  React SPA     │          │   (Uvicorn)     │
     └────────────────┘          └──────────┬──────┘
                                            │
                             ┌──────────────┴──────────────┐
                             │                             │
                    ┌────────┴───────┐         ┌───────────┴──────┐
                    │   PostgreSQL   │         │    ChromaDB       │
                    │   Port 5432    │         │   (Local Persist) │
                    └────────────────┘         └──────────────────┘
```

---

## Prerequisites

- Docker 24+
- Docker Compose v2
- 4GB RAM minimum (8GB recommended for LLM operations)
- GROQ_API_KEY (from https://console.groq.com/)
- GOOGLE_API_KEY (optional, for Gemini embeddings)

---

## Quick Start (Local Development)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ipo-copilot-ai.git
cd ipo-copilot-ai

# 2. Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env and set:
#   GROQ_API_KEY=your_groq_key
#   SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 3. Start services
docker compose up --build

# 4. Seed initial data
docker exec ipo_backend python -m app.seed

# 5. Access
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Production Deployment

### Step 1: Environment Setup
```bash
cp backend/.env.example .env

# Required values:
POSTGRES_PASSWORD=<generate-strong-password>
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
GROQ_API_KEY=<your-groq-api-key>
GOOGLE_API_KEY=<your-google-api-key>

# Production origins only:
ALLOWED_ORIGINS=https://your-domain.com
```

### Step 2: Build and Start
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### Step 3: Run Migrations
```bash
docker exec ipo_backend_prod alembic upgrade head
```

### Step 4: Seed Data
```bash
docker exec ipo_backend_prod python -m app.seed
```

### Step 5: Health Check
```bash
curl https://your-domain.com/health
# Expected: {"status": "healthy", "database": "connected", ...}
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | SQLite | PostgreSQL: `postgresql+asyncpg://...` |
| `SECRET_KEY` | Yes | None | 32-byte random hex for JWT signing |
| `GROQ_API_KEY` | Yes | None | Groq LLM API key |
| `GOOGLE_API_KEY` | No | None | Google Gemini API key |
| `LLM_PROVIDER` | No | groq | `groq` or `google` |
| `LLM_MODEL` | No | llama-3.3-70b-versatile | Model name |
| `EMBEDDING_MODEL` | No | all-MiniLM-L6-v2 | Sentence transformer model |
| `CHROMA_PERSIST_DIR` | No | ./chroma_db | ChromaDB storage path |
| `UPLOAD_DIR` | No | ./uploads | Document upload directory |
| `MAX_UPLOAD_SIZE_MB` | No | 50 | Maximum file upload size |
| `ALLOWED_ORIGINS` | No | localhost:5173 | CORS allowed origins |
| `POSTGRES_PASSWORD` | Prod | None | PostgreSQL password (Docker) |

---

## Health Checks

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Backend health + DB connectivity |
| `GET /nginx-health` | Frontend nginx health |
| `GET /docs` | OpenAPI documentation |

---

## Scaling Considerations

### Horizontal Scaling
The backend uses async SQLAlchemy and is stateless (JWT auth). Multiple instances can run behind a load balancer. Ensure:
- All instances share the same PostgreSQL database
- ChromaDB is on shared storage (NFS or S3) OR use a hosted vector DB

### Vertical Scaling
- LLM generation is CPU/network bound (Groq API calls)
- Increase `pool_size` in database.py for high traffic
- ChromaDB performance improves with more RAM

---

## Security Checklist (Pre-Launch)

- [ ] Rotate GROQ_API_KEY and GOOGLE_API_KEY
- [ ] Generate a strong SECRET_KEY (32+ byte random)
- [ ] Enable HTTPS with valid TLS certificate
- [ ] Set ALLOWED_ORIGINS to production domain only
- [ ] Configure PostgreSQL with strong password and non-default port
- [ ] Enable database connection encryption (SSL mode)
- [ ] Set up automated backups
- [ ] Configure log aggregation (Datadog, Sentry, etc.)
- [ ] Enable HSTS header (auto-enabled for HTTPS in SecurityHeadersMiddleware)
- [ ] Review and tighten CORS policy

---

## Logs

```bash
# Backend logs
docker logs ipo_backend_prod -f

# Frontend nginx logs
docker logs ipo_frontend_prod -f

# PostgreSQL logs
docker logs ipo_postgres_prod -f
```

---

## Upgrading

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker compose -f docker-compose.prod.yml up --build -d

# Apply any new migrations
docker exec ipo_backend_prod alembic upgrade head
```

---

## Demo Credentials

For the hackathon demo:
- **Email:** demo@ipocolpilot.ai
- **Password:** Demo@1234
- **Role:** analyst
