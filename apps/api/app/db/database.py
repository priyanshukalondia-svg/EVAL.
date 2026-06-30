# apps/api/app/db/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database URL configuration
# Default to SQLite inside the apps/api directory for local development, but support PostgreSQL via env var
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./recruitment.db"
)

# Connect args specific to SQLite (needed for multi-thread support)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative Base for models
Base = declarative_base()

def get_db():
    """Dependency injection helper for FastAPI routes to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables. In production, Alembic migrations should be used."""
    # Enforce SQLite foreign key constraints
    if DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
    Base.metadata.create_all(bind=engine)
