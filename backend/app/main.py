from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import complaints

# ─────────────────────────────────────────────────────────
#  Initialize FastAPI app
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="AI-Powered Customer Complaint Management System",
    description=(
        "A pharmaceutical QMS complaint intake API.\n\n"
        "Supports complaint creation, retrieval, and (in later phases) "
        "AI-powered extraction, validation, risk assessment, and completeness checks "
        "via LangGraph + Groq."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─────────────────────────────────────────────────────────
#  CORS — allow all origins during development
#  (restrict in production before deployment)
# ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
#  Auto-create database tables on startup
#  (SQLAlchemy will skip already-existing tables)
# ─────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────
#  Mount routers
# ─────────────────────────────────────────────────────────
app.include_router(complaints.router)

# ─────────────────────────────────────────────────────────
#  Health check
# ─────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "AI Complaint Management API is running."}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
