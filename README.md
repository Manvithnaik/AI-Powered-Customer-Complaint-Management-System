# 🧪 AI-Powered Customer Complaint Management System

> **An enterprise-grade, AI-augmented Quality Management System (QMS) for pharmaceutical complaint intake, triage, and analysis — built with FastAPI, LangGraph, Groq, PostgreSQL, and React.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-FF6B35?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-Deploy-0B0D0E?style=flat-square&logo=railway&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 📋 Project Overview

Pharmaceutical manufacturers are legally obligated under **FDA 21 CFR Part 211** and **EU GMP Annex 15** to record, investigate, and resolve every product complaint through a Quality Management System (QMS). In practice, complaint intake is largely manual — QA engineers parse emails, faxes, and portal submissions, then transcribe data into structured systems. This process is slow, error-prone, and inconsistent.

This system replaces that manual intake process with an **AI-first complaint pipeline**:

1. A QA engineer pastes raw complaint text or uploads a PDF.
2. An **8-node LangGraph pipeline** automatically extracts structured facts, assesses risk, generates a Root Cause Analysis (RCA), recommends Corrective and Preventive Actions (CAPA), checks for duplicate complaints, and scores data completeness.
3. The QA engineer reviews AI-generated output in **read-only mode**, then edits only where corrections are needed.
4. Structured complaint records are saved to **PostgreSQL** and immediately retrievable via REST API.

**Key pharmaceutical domain concepts implemented:**
| Term | Meaning |
|---|---|
| **QMS** | Quality Management System — the formal framework for complaint handling under GMP regulations |
| **API** | Active Pharmaceutical Ingredient — the drug substance in a formulation |
| **FDF** | Finished Dosage Form — the final consumer product (tablet, capsule, vial) |
| **Batch/Lot Number** | Unique manufacturing identifier enabling full product traceability |
| **CAPA** | Corrective and Preventive Action — mandated response to a confirmed defect |
| **RCA** | Root Cause Analysis — systematic investigation of defect origin |
| **Severity** | Criticality classification: Critical / Major / Minor |

---

## ✨ Features

### 📝 Complaint Management
- **AI Complaint Extraction** — Automatically extracts 15+ structured fields from raw text
- **PDF Upload** — Parse complaint documents directly using PyMuPDF
- **Manual Complaint Entry** — Full form-based entry with field validation
- **Read-Only / Edit Mode Toggle** — AI output is protected until QA engineer approves edits
- **Complaint Storage** — PostgreSQL-backed persistent storage with auto-generated complaint IDs (`CMP-YYYY-XXXX`)
- **Complaint Retrieval** — List, filter, and retrieve complaints via REST API with full pagination

### 🤖 AI Intelligence (LangGraph Pipeline)
- **Risk Assessment** — Automated severity (Critical / Major / Minor) and priority (High / Medium / Low) classification with rationale
- **Complaint Completeness Checker** — Scores data completeness and flags missing required fields
- **Executive QA Summary** — Structured paragraph summary for management reporting
- **Root Cause Recommendation (RCA)** — Generates pharmaceutical-domain RCA hypotheses (mechanical, microbiological, human error, supply chain)
- **CAPA Recommendation** — Produces actionable corrective and preventive action steps
- **Duplicate Complaint Detection** — Semantic similarity check against existing complaints with confidence scoring

### 🏢 Enterprise Features
- **PostgreSQL Database** — Production-grade relational data store with JSONB for AI analytics
- **8-Node LangGraph Workflow** — Deterministic, inspectable AI pipeline with typed state
- **Structured Complaint Records** — Complete pharmaceutical QMS data model
- **Full REST API** — OpenAPI 3.0 spec, Swagger UI, and ReDoc documentation
- **Modern React Dashboard** — Split-panel QA workstation with AI Copilot sidebar
- **Toast Notifications** — Non-blocking status feedback throughout the workflow
- **Docker + Railway Deployment** — Production-ready containerized deployment

---

## 🛠 Tech Stack

| Category | Technology |
|---|---|
| **Frontend** | React 18, Vite |
| **State Management** | Redux Toolkit |
| **Styling** | Vanilla CSS with CSS Custom Properties |
| **Backend** | Python 3.12, FastAPI 0.111 |
| **AI Orchestration** | LangGraph (StateGraph) |
| **AI Inference** | Groq API (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`) |
| **Database** | PostgreSQL 16 (Supabase / Neon / Railway) |
| **ORM** | SQLAlchemy 2.0 |
| **Document Parsing** | PyMuPDF (fitz) |
| **Data Validation** | Pydantic v2 |
| **Deployment** | Docker (`python:3.12-slim`), Railway, Vercel |
| **Version Control** | Git / GitHub |

---

## 🏗 System Architecture

```mermaid
graph TB
    subgraph Frontend ["🖥️ React Frontend (Vercel)"]
        UI[QA Workstation Dashboard]
        CF[Complaint Form\nRead-Only / Edit Mode]
        AC[AI Copilot Sidebar\n6-Stage Progress Loader]
        TN[Toast Notifications]
        RX[(Redux Store\ncomplaintSlice)]
    end

    subgraph Backend ["⚙️ FastAPI Backend (Railway)"]
        API[REST API\n/api/complaints\n/api/ai/analyze]
        LG[LangGraph Pipeline\n8-Node StateGraph]
        EX[Extractor\nllama-3.1-8b-instant]
        CRUD[SQLAlchemy CRUD]
    end

    subgraph AI ["🤖 Groq LLM Layer"]
        FM[Fast Model\nllama-3.1-8b-instant\nExtraction · Summary · Dedup]
        RM[Reasoning Model\nllama-3.3-70b-versatile\nRisk · RCA · CAPA]
    end

    subgraph DB ["🗄️ PostgreSQL"]
        PG[(complaints table\nJSONB AI analytics)]
    end

    UI -->|Paste text / Upload PDF| API
    CF -->|Edit & Save| API
    AC -->|Polling for AI output| RX
    API --> LG
    LG --> EX
    EX --> FM
    LG --> RM
    LG --> CRUD
    CRUD --> PG
    API --> PG
    RX -->|Dispatch actions| API
```

---

## 📁 Folder Structure

```
AI-Powered-Customer-Complaint-Management-System/
│
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py            # LangGraph StateGraph (8-node pipeline)
│   │   │   ├── nodes.py            # All 8 node implementations
│   │   │   ├── state.py            # TypedDict ComplaintState definition
│   │   │   ├── extractor.py        # Groq AI fact extraction (llama-3.1-8b-instant)
│   │   │   ├── document_parser.py  # PDF parsing via PyMuPDF
│   │   │   ├── date_utils.py       # Date string normalization utility
│   │   │   └── __init__.py
│   │   ├── routers/
│   │   │   ├── complaints.py       # CRUD REST endpoints
│   │   │   ├── ai.py               # AI analysis endpoints
│   │   │   └── __init__.py
│   │   ├── main.py                 # FastAPI app, lifespan, CORS
│   │   ├── database.py             # SQLAlchemy engine + session factory
│   │   ├── models.py               # Complaint SQLAlchemy model
│   │   ├── schemas.py              # Pydantic v2 request / response schemas
│   │   ├── crud.py                 # Database CRUD helpers
│   │   └── __init__.py
│   ├── Dockerfile                  # python:3.12-slim production image
│   ├── railway.json                # Railway build + deploy configuration
│   ├── .python-version             # Python 3.12.4 version pin
│   ├── .env.example                # Environment variable template
│   ├── requirements.txt            # Python dependencies
│   ├── seed_db.py                  # Sample data seeder
│   ├── test_db.py                  # Database connection / CRUD tests
│   ├── test_extraction.py          # Groq extraction integration tests
│   ├── test_langgraph.py           # LangGraph pipeline tests
│   └── test_phase5.py              # Full backend integration tests
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ComplaintForm.jsx   # Split-panel complaint form (Read-Only / Edit)
│   │   │   ├── ComplaintForm.css
│   │   │   ├── AiCopilot.jsx      # AI Copilot sidebar + 6-stage loader
│   │   │   ├── AiCopilot.css
│   │   │   ├── Header.jsx         # Application header bar
│   │   │   ├── Header.css
│   │   │   ├── Toast.jsx          # Toast notification system
│   │   │   └── Toast.css
│   │   ├── store/
│   │   │   └── complaintSlice.js  # Redux Toolkit slice
│   │   ├── services/
│   │   │   └── api.js             # Axios API service layer
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css              # Global design system tokens
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── railway.json                    # Root Railway monorepo configuration
├── .gitignore
└── README.md
```

---

## 🔄 Application Workflow

```mermaid
flowchart TD
    A([QA Engineer]) -->|Pastes complaint text\nor uploads PDF| B[FastAPI /api/ai/analyze]
    B --> C[LangGraph Pipeline Invoked]

    subgraph Pipeline ["8-Node LangGraph StateGraph"]
        direction TB
        N1[1. Extraction Node\nGroq llama-3.1-8b-instant\nExtracts 15+ structured fields]
        N2[2. Validation Node\nPure Python\nDate normalization · field checks]
        N3[3. Risk Assessment Node\nGroq llama-3.3-70b-versatile\nSeverity · Priority · Rationale]
        N4[4. Completeness Check Node\nPure Python\nScores missing fields]
        N5[5. Summary Node\nGroq llama-3.1-8b-instant\nExecutive QA summary]
        N6[6. RCA Node\nGroq llama-3.3-70b-versatile\nRoot cause hypotheses]
        N7[7. CAPA Node\nGroq llama-3.3-70b-versatile\nCorrective · Preventive actions]
        N8[8. Duplicate Detection Node\nGroq llama-3.1-8b-instant\nSemantic similarity scoring]
        N1 --> N2 --> N3 --> N4 --> N5 --> N6 --> N7 --> N8
    end

    C --> N1
    N8 --> D[ComplaintState returned to API]
    D --> E[React Dashboard\nForm auto-populated in Read-Only mode]
    E --> F{QA Review}
    F -->|No corrections needed| G[Click Save — POST /api/complaints]
    F -->|Corrections required| H[Click Edit Complaint\nForm becomes editable]
    H --> I[Make corrections] --> G
    G --> J[(PostgreSQL\nCMP-YYYY-XXXX stored)]
```

---

## 🗄 Database Schema

The `complaints` table captures the full pharmaceutical QMS data model:

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER` PK | Auto-increment primary key |
| `complaint_number` | `VARCHAR(50)` UNIQUE | Auto-generated ID: `CMP-YYYY-XXXX` |
| `complaint_source` | `VARCHAR(100)` | Origin channel: Email, Phone, Portal, Letter |
| `customer_name` | `VARCHAR(255)` | Pharmacy, hospital, or distributor name |
| `product_name` | `VARCHAR(255)` | Pharmaceutical product name |
| `product_strength_grade` | `VARCHAR(100)` | Strength/grade (e.g. 500mg, Grade A) |
| `batch_lot_number` | `VARCHAR(100)` | Batch/lot number for traceability |
| `manufacturing_date` | `DATE` | Date of manufacture |
| `expiry_date` | `DATE` | Product expiry date |
| `quantity_affected` | `VARCHAR(100)` | Affected quantity (e.g. "20 strips") |
| `complaint_type` | `VARCHAR(255)` | Defect category (e.g. Contamination) |
| `complaint_date` | `DATE` | Date complaint was raised |
| `detailed_description` | `TEXT` | Full raw complaint narrative |
| `initial_severity` | `VARCHAR(50)` | AI-assessed: Critical / Major / Minor |
| `priority` | `VARCHAR(50)` | AI-assessed: High / Medium / Low |
| `status` | `VARCHAR(50)` | Pending Triage / Under Investigation / Resolved |
| `ai_completeness_check` | `JSON` | Completeness score + missing fields list |
| `ai_risk_rationale` | `TEXT` | AI rationale for severity/priority rating |
| `ai_complaint_summary` | `TEXT` | Executive QA summary paragraph |
| `ai_capa_rca` | `JSON` | RCA hypotheses array |
| `ai_capa_recommendation` | `JSON` | CAPA corrective/preventive actions array |
| `created_at` | `TIMESTAMP` | Record creation timestamp |
| `updated_at` | `TIMESTAMP` | Last update timestamp |

---

## 🤖 AI Pipeline — Node Reference

| # | Node | Model | Input | Output |
|---|---|---|---|---|
| 1 | **Extraction** | `llama-3.1-8b-instant` | Raw complaint text | 15+ structured fields (product, batch, dates, description, customer) |
| 2 | **Validation** | Pure Python | Extracted fields | Normalized dates, field presence warnings, `validation_passed` flag |
| 3 | **Risk Assessment** | `llama-3.3-70b-versatile` | Extracted fields + description | `initial_severity`, `priority`, `ai_risk_rationale` |
| 4 | **Completeness Check** | Pure Python | All extracted fields | `ai_completeness_check` — score (0–100) + list of missing fields |
| 5 | **Summary** | `llama-3.1-8b-instant` | Extracted fields + description | `ai_complaint_summary` — executive paragraph for QA management |
| 6 | **RCA** | `llama-3.3-70b-versatile` | Full complaint context | `ai_capa_rca` — root cause hypotheses with pharmaceutical domain reasoning |
| 7 | **CAPA** | `llama-3.3-70b-versatile` | RCA output + complaint context | `ai_capa_recommendation` — corrective and preventive action steps |
| 8 | **Duplicate Detection** | `llama-3.1-8b-instant` | New complaint + existing records | `ai_duplicate_check` — similarity score, matched complaint IDs, confidence |

---

## 📸 Screenshots

### Dashboard — QA Workstation

> *Add screenshot here — full split-panel view showing the Complaint Form (left) and AI Copilot sidebar (right)*

### AI Processing — 6-Stage Progressive Loader

> *Add screenshot here — showing the animated pipeline stages during LangGraph execution*

### Complaint Form — Read-Only Mode

> *Add screenshot here — form auto-populated with AI-extracted data, read-only state with "AI GENERATED" badge*

### Complaint Form — Edit Mode

> *Add screenshot here — form in edit mode after clicking "✏ Edit Complaint", with "MANUAL EDITING" badge*

### AI Copilot — Analysis Results

> *Add screenshot here — Risk Assessment, Summary, RCA, CAPA, Duplicate Detection, and Completeness score panels*

### Duplicate Detection

> *Add screenshot here — showing duplicate complaint similarity score and matched complaint reference*

---

## 🚀 Local Installation & Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL database (Supabase or Neon recommended)
- Groq API Key — [console.groq.com](https://console.groq.com)

### 1. Clone the Repository

```bash
git clone https://github.com/Manvithnaik/AI-Powered-Customer-Complaint-Management-System.git
cd AI-Powered-Customer-Complaint-Management-System
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
GROQ_API_KEY=gsk_your_groq_api_key_here
MODEL_NAME=llama-3.1-8b-instant
ALLOWED_ORIGINS=http://localhost:5173
```

### 4. Run the Backend API Server

```bash
# Development (with hot reload)
uvicorn app.main:app --reload --port 8000
```

- API Base: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

### 5. Frontend Setup

```bash
# In a new terminal, from the repo root
cd frontend
npm install
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 6. (Optional) Seed Sample Data

```bash
# From backend/ directory with .venv active
python seed_db.py
```

---

## 🔐 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string (with `?sslmode=require` for cloud) | ✅ Yes |
| `GROQ_API_KEY` | Groq API key from [console.groq.com](https://console.groq.com) | ✅ Yes |
| `MODEL_NAME` | Fast LLM model name (default: `llama-3.1-8b-instant`) | ✅ Yes |
| `ALLOWED_ORIGINS` | Comma-separated list of permitted frontend URLs for CORS | ✅ Yes |

> **Note:** Never commit your `.env` file. It is included in `.gitignore` by default.

---

## 📡 API Endpoints

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check — returns `{"status": "healthy"}` |

### Complaint Management

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/complaints/` | Create a new complaint record |
| `GET` | `/api/complaints/` | List all complaints (supports `skip` / `limit` pagination) |
| `GET` | `/api/complaints/{id}` | Retrieve a single complaint by ID |
| `PATCH` | `/api/complaints/{id}` | Partially update complaint fields |
| `DELETE` | `/api/complaints/{id}` | Delete a complaint record |

### AI Analysis

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ai/analyze` | Run the full 8-node LangGraph pipeline on raw complaint text |
| `POST` | `/api/ai/analyze-pdf` | Upload and analyze a PDF complaint document |

<details>
<summary><strong>Example: POST /api/ai/analyze</strong></summary>

**Request Body:**
```json
{
  "raw_text": "Dear QA team, we received a complaint from MedPlus pharmacy regarding batch B-2024-0912 of our Amoxicillin 500mg capsules. The customer reports 3 out of 10 strips had discoloured tablets with an unusual odour. Date of complaint: 2024-11-15. Customer: MedPlus Pharmacy, Hyderabad."
}
```

**Response (200 OK):**
```json
{
  "extracted_fields": {
    "product_name": "Amoxicillin",
    "product_strength_grade": "500mg",
    "batch_lot_number": "B-2024-0912",
    "customer_name": "MedPlus Pharmacy",
    "complaint_type": "Discolouration / Odour defect"
  },
  "initial_severity": "Major",
  "priority": "High",
  "ai_risk_rationale": "Discolouration and unusual odour in antibiotic capsules indicate potential degradation or contamination, requiring immediate quarantine and investigation.",
  "ai_complaint_summary": "MedPlus Pharmacy reported discolouration and odour in Amoxicillin 500mg capsules from batch B-2024-0912...",
  "ai_capa_rca": [...],
  "ai_capa_recommendation": [...],
  "ai_completeness_check": { "score": 78, "missing_fields": ["manufacturing_date", "quantity_affected"] },
  "ai_duplicate_check": { "is_duplicate": false, "similarity_score": 0.12 }
}
```
</details>

---

## 🔮 Future Improvements

- [ ] **Authentication & RBAC** — JWT-based login with role-based access (QA Engineer, QA Manager, Admin)
- [ ] **Email Integration** — Auto-ingest complaints from a monitored inbox using IMAP/SMTP
- [ ] **Audit Trail** — Immutable change log for every complaint update (21 CFR Part 11 compliance)
- [ ] **Analytics Dashboard** — Trend charts for complaint volume, severity distribution, and resolution time
- [ ] **Batch Recall Correlation** — Automatically link related complaints to the same batch/lot
- [ ] **Regulatory Report Generation** — Export complaints in FDA MedWatch or EMA format
- [ ] **Webhook Notifications** — Slack / Teams alerts for Critical severity complaints
- [ ] **Multi-language Support** — NLP extraction for complaints submitted in non-English languages

---

## 👤 Author

**Manvith Naik**

[![GitHub](https://img.shields.io/badge/GitHub-Manvithnaik-181717?style=flat-square&logo=github)](https://github.com/Manvithnaik)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat-square&logo=linkedin)](https://linkedin.com/in/your-linkedin-profile)

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Manvith Naik

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">
  <sub>Built with ❤️ for pharmaceutical QMS modernisation</sub>
</div>
