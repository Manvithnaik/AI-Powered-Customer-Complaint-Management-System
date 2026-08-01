import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import complaints, ai


# ─────────────────────────────────────────────────────────
#  Lifespan — runs on startup / shutdown (replaces deprecated @on_event)
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create database tables (SQLAlchemy skips already-existing tables)
    Base.metadata.create_all(bind=engine)
    yield


# ─────────────────────────────────────────────────────────
#  Initialize FastAPI app
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="AI-Powered Customer Complaint Management System",
    description=(
        "A pharmaceutical QMS complaint intake API.\n\n"
        "Supports complaint creation, retrieval, AI-powered extraction, "
        "validation, risk assessment, completeness checking, executive summary, "
        "root cause analysis, CAPA recommendations, and duplicate detection "
        "via LangGraph + Groq."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────
#  CORS — origins are controlled via the ALLOWED_ORIGINS env variable.
#  Set ALLOWED_ORIGINS=https://your-frontend.com in production.
#  Falls back to localhost:5173 for local development.
# ─────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
#  Mount routers
# ─────────────────────────────────────────────────────────
app.include_router(complaints.router)
app.include_router(ai.router)


# ─────────────────────────────────────────────────────────
#  Health check
# ─────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "AI Complaint Management API is running."}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
