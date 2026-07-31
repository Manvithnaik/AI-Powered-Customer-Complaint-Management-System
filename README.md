# AI-Powered Customer Complaint Management System

A pharmaceutical QMS complaint intake system built with FastAPI, LangGraph, Groq, PostgreSQL, and React.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Redux Toolkit |
| Backend | Python + FastAPI |
| AI Orchestration | LangGraph |
| AI Inference | Groq API (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`) |
| Database | PostgreSQL (Supabase cloud) |
| ORM | SQLAlchemy |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── extractor.py       # Groq AI fact extraction (Phase 3)
│   │   │   ├── date_utils.py      # Date string normalization utility
│   │   │   └── __init__.py
│   │   ├── routers/
│   │   │   ├── complaints.py      # FastAPI REST endpoints
│   │   │   └── __init__.py
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── database.py            # SQLAlchemy engine + session
│   │   ├── models.py              # Complaint SQLAlchemy model
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   ├── crud.py                # Database CRUD helpers
│   │   └── __init__.py
│   ├── requirements.txt
│   ├── .env.example               # Template — copy to .env and fill in secrets
│   ├── test_db.py                 # Phase 1: DB connection + CRUD verification
│   ├── test_extraction.py         # Phase 3: Groq extraction integration test
│   └── seed_db.py                 # Push sample seed data to PostgreSQL
└── frontend/                      # Phase 6 — React + Redux (coming soon)
```

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Manvithnaik/AI-Powered-Customer-Complaint-Management-System.git
cd AI-Powered-Customer-Complaint-Management-System
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   DATABASE_URL — your PostgreSQL connection string (Supabase/Neon)
#   GROQ_API_KEY — your Groq API key from console.groq.com
```

### 4. Run the API server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** for the Swagger interactive API documentation.

### 5. Run verification tests

```bash
# Phase 1 — Database connection test
python test_db.py

# Phase 3 — Groq AI extraction test
python test_extraction.py
```

## Development Phases

| Phase | Description | Status |
|---|---|---|
| Phase 1 | PostgreSQL Data Layer (SQLAlchemy models, schema) | ✅ Complete |
| Phase 2 | FastAPI CRUD API (POST, GET, PATCH, DELETE) | ✅ Complete |
| Phase 3 | Groq AI Extraction (Fact extraction from raw text) | ✅ Complete |
| Phase 4 | LangGraph Workflow (Extract → Validate → Risk → Completeness) | 🔄 In Progress |
| Phase 5 | Full Backend Integration Test | ⏳ Pending |
| Phase 6 | React + Redux Frontend | ⏳ Pending |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/complaints/` | Create a new complaint |
| `GET` | `/api/complaints/` | List all complaints (with pagination) |
| `GET` | `/api/complaints/{id}` | Get a complaint by ID |
| `PATCH` | `/api/complaints/{id}` | Update complaint fields |
| `DELETE` | `/api/complaints/{id}` | Delete a complaint |

## Note on Model Selection

The assignment specifies `gemma2-9b-it` via Groq. This model was decommissioned by Groq on 2026-07-31. We use `llama-3.1-8b-instant` as the direct replacement for fast extraction tasks, and `llama-3.3-70b-versatile` for deep reasoning (risk assessment). Both are available on Groq and maintain equivalent performance profiles.

## Assignment Context

Built as a hiring assignment for AI Product Engineer role — demonstrating:
- Product thinking and MVP-first development
- Clean AI integration with LangGraph orchestration
- Pharmaceutical QMS domain knowledge (API vs FDF, batch traceability, severity triage)
- End-to-end full stack delivery
