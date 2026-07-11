# 🚀 IPO Copilot AI

> **AI-Driven Assistant for SME IPO Document Preparation & SEBI Compliance**
>
> Built for the SEBI Hackathon — empowering investment bankers and SMEs to navigate the IPO journey with confidence.

---

## 📋 Project Overview

IPO Copilot AI is a production-ready, AI-powered platform that automates and accelerates the preparation of SME IPO documents in compliance with SEBI regulations. It combines a Retrieval-Augmented Generation (RAG) pipeline, real-time DRHP validation, and an intelligent copilot chat interface to reduce document preparation time from weeks to days.

**Core Capabilities:**
- 📄 **Document Intelligence** — Upload and parse DRHP, financial statements, legal disclosures
- ✅ **SEBI Compliance Validation** — Automated checks against ICDR Regulations 2018
- 🤖 **AI Copilot Chat** — Context-aware Q&A grounded in SEBI circulars and your documents
- 🔍 **Draft Review Engine** — Section-level gap analysis and actionable suggestions
- 📊 **Workspace Dashboard** — Multi-company, multi-document project management

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│              React 18 + Vite + TailwindCSS                      │
│         (Dashboard · Copilot Chat · Validation · Review)        │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST / WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                       API LAYER (Port 8000)                     │
│              FastAPI 0.111 · Python 3.11 · Uvicorn              │
│    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│    │  /auth   │ │  /docs   │ │/validate │ │    /copilot      │ │
│    │  /users  │ │/workspce │ │ /review  │ │  (SSE stream)    │ │
│    └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
└──────────┬───────────────┬───────────────────┬──────────────────┘
           │               │                   │
┌──────────▼──────┐ ┌──────▼──────┐  ┌────────▼───────────┐
│   PostgreSQL 16 │ │  ChromaDB   │  │   OpenAI API       │
│  (Port 5432)    │ │ (Vector DB) │  │  GPT-4o-mini       │
│                 │ │             │  │  text-embedding-3  │
│ • Users         │ │ • SEBI docs │  │  -small            │
│ • Companies     │ │ • DRHP      │  └────────────────────┘
│ • Workspaces    │ │   chunks    │
│ • Documents     │ │ • Circular  │
│ • Validations   │ │   embeddings│
│ • Chat history  │ └─────────────┘
└─────────────────┘
```

---

## ⚙️ Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker Desktop | 24+ | Required for all services |
| Docker Compose | v2+ | Bundled with Docker Desktop |
| Node.js | 20 LTS | For local frontend dev only |
| Python | 3.11+ | For local backend dev only |
| OpenAI API Key | — | Required for AI features |

---

## 🚀 Quick Start

### 1. Clone & Configure

```bash
git clone <repo-url>
cd "SEBI HACKATHON"

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Launch All Services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **FastAPI Backend** on `localhost:8000`
- **React Frontend** on `localhost:3000`

### 3. Access the Application

| Service | URL |
|---|---|
| 🌐 Frontend App | http://localhost:3000 |
| 📡 API Server | http://localhost:8000 |
| 📚 API Docs (Swagger) | http://localhost:8000/docs |
| 📖 API Docs (ReDoc) | http://localhost:8000/redoc |

### 4. Stop Services

```bash
docker compose down          # Stop containers
docker compose down -v       # Stop + remove volumes (fresh start)
```

---

## 🔑 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `hackathon-secret-key` | JWT signing secret — **change in production** |
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key for GPT-4o-mini & embeddings |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model to use |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `DATABASE_URL` | *(set by compose)* | PostgreSQL connection string |
| `CHROMA_PERSIST_DIR` | `/app/chroma_db` | ChromaDB vector store directory |
| `UPLOAD_DIR` | `/app/uploads` | Uploaded document storage path |

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11 | Runtime |
| FastAPI | 0.111 | REST API framework |
| SQLAlchemy | 2.0 | Async ORM |
| Alembic | 1.13 | Database migrations |
| PostgreSQL | 16 | Primary database |
| ChromaDB | 0.5 | Vector store for RAG |
| LangChain | 0.2 | RAG pipeline orchestration |
| OpenAI | 1.30 | LLM & embeddings |
| PyMuPDF | 1.24 | PDF parsing |
| python-jose | 3.3 | JWT authentication |
| Pydantic | 2.7 | Data validation |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 18 | UI framework |
| Vite | 5 | Build tool & dev server |
| TailwindCSS | 3 | Styling |
| React Query | 5 | Server state management |
| Zustand | 4 | Client state management |
| React Router | 6 | Client-side routing |
| Axios | 1.7 | HTTP client |

### Infrastructure
| Technology | Purpose |
|---|---|
| Docker & Compose | Containerization & orchestration |
| PostgreSQL 16 | Relational data storage |
| ChromaDB | Persistent vector embeddings |

---

## 📁 Project Structure

```
SEBI HACKATHON/
├── docker-compose.yml          # Multi-service orchestration
├── .env.example                # Environment variable template
├── .gitignore
├── README.md
│
├── backend/                    # FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              # Async migration env
│   │   └── versions/           # Migration scripts
│   └── app/
│       ├── main.py             # FastAPI app entry point
│       ├── config.py           # Settings (pydantic-settings)
│       ├── database.py         # Async SQLAlchemy engine
│       ├── models/             # SQLAlchemy ORM models
│       ├── schemas/            # Pydantic request/response schemas
│       ├── routers/            # API route handlers
│       ├── services/           # Business logic layer
│       ├── ai/                 # RAG pipeline & LLM services
│       ├── middleware/         # Auth, logging, CORS middleware
│       └── utils/              # Shared utilities
│
└── frontend/                   # React application
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── components/         # Reusable UI components
        ├── pages/              # Route-level page components
        ├── hooks/              # Custom React hooks
        ├── stores/             # Zustand state stores
        ├── services/           # API client functions
        └── types/              # TypeScript type definitions
```

---

## 👥 Team Structure

| Role | Responsibility |
|---|---|
| **Dev 1 — Backend Lead** | FastAPI core, auth, database models, migrations |
| **Dev 2 — AI/RAG Engineer** | ChromaDB pipeline, LangChain integration, embeddings |
| **Dev 3 — Compliance Engineer** | SEBI validation rules, compliance checks, regulation parser |
| **Dev 4 — Frontend Lead** | React UI, dashboard, document upload, state management |
| **Dev 5 — Full-Stack / Integration** | Copilot chat UI + SSE, review engine, E2E integration |

---

## 📅 8-Day Development Roadmap

| Day | Milestone |
|---|---|
| **Day 1** | Repo setup, Docker infra, DB schema, base FastAPI app |
| **Day 2** | Auth system, user/company/workspace CRUD APIs |
| **Day 3** | Document upload, PDF parsing, ChromaDB ingestion pipeline |
| **Day 4** | SEBI compliance validation engine (rule-based + LLM) |
| **Day 5** | Copilot chat with RAG (streaming SSE), session history |
| **Day 6** | Draft review engine, section gap analysis |
| **Day 7** | Frontend pages: Dashboard, Upload, Chat, Validation Report |
| **Day 8** | Integration testing, demo data seeding, polish & deploy |

---

## 📜 License

This project was built for the SEBI Hackathon. All rights reserved.

---

*Built with ❤️ for India's SME IPO ecosystem*
