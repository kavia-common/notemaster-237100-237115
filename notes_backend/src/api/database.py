"""
Database connection configuration for the NoteMaster backend.
Uses SQLAlchemy async engine connected to PostgreSQL via environment variables.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read connection details from environment variables (set by the platform)
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "dbuser123")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://localhost:5000/myapp")
POSTGRES_DB = os.getenv("POSTGRES_DB", "myapp")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5000")

# Build the full connection URL with credentials
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)

# Session factory for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for ORM models
Base = declarative_base()


# PUBLIC_INTERFACE
def get_db():
    """
    Dependency that provides a database session.
    Yields a SQLAlchemy session and ensures it is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
