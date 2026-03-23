# Chronos — PostgreSQL Database Layer (Render Deployment)

import os

# Use PostgreSQL via SQLAlchemy ORM
# DATABASE_URL is set in Render environment or .env for local development
from .postgres_schema import SessionLocal

def init_database():
    """No-op for now. Tables created lazily on first query."""
    pass

__all__ = ["init_database", "SessionLocal"]
