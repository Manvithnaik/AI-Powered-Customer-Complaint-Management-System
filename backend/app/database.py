import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Enforce PostgreSQL constraint (no SQLite fallback)
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is missing. Please set your PostgreSQL database connection URL in backend/.env"
    )

if not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")):
    raise ValueError(
        f"Invalid connection URL: '{DATABASE_URL[:15]}...'. The database URL must start with 'postgresql://' or 'postgres://'."
    )

# Setup connection pooling for cloud databases (PostgreSQL)
engine_args = {
    "pool_pre_ping": True,  # Checks connection liveness before executing queries
    "pool_recycle": 1800,   # Recycle connections after 30 minutes to prevent timeouts
    "pool_size": 5,
    "max_overflow": 10,
}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get db session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
