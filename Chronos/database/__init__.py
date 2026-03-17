# Chronos — Dual-mode database layer (SQLite local, PostgreSQL production)

import os

# Detect which database to use
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL and ("postgresql://" in DATABASE_URL or "postgres://" in DATABASE_URL):
    # Production: Use PostgreSQL via SQLAlchemy ORM
    try:
        from .postgres_schema import init_database, SessionLocal
    except ImportError:
        # Fallback to SQLite if PostgreSQL dependencies unavailable
        from .schema import init_database
        SessionLocal = None
else:
    # Development: Use SQLite
    from .schema import init_database
    SessionLocal = None

__all__ = ["init_database", "SessionLocal"]
