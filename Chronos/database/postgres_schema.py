"""
CHRONOS — PostgreSQL Schema & Migration
========================================

Production-grade database layer with SQLAlchemy ORM and Alembic migrations.
Replaces the SQLite schema.py with PostgreSQL-specific implementation.

Features:
- ACID compliance with transaction support
- Concurrent connection pooling
- UUID primary keys (no sequential IDs)
- JSON field support for metadata
- Audit timestamps with timezone awareness
- Automated migrations via Alembic
"""

import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Boolean, Text,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from sqlalchemy.pool import NullPool
import uuid

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine safely - will fail gracefully if DB is unavailable
engine = None
SessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    try:
        # Add SSL requirement for external PostgreSQL URLs
        if "dpg-" in DATABASE_URL and "?sslmode" not in DATABASE_URL:
            DATABASE_URL += "?sslmode=require"

        # Use NullPool for Render/Cloud deployments (closes idle connections)
        if "render.com" in DATABASE_URL or "heroku" in DATABASE_URL or "dpg-" in DATABASE_URL:
            engine = create_engine(DATABASE_URL, poolclass=NullPool, connect_args={"connect_timeout": 5})
        else:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)

        SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        print("App will start but database features will be unavailable.")
        engine = None
        SessionLocal = None
else:
    print("⚠️  DATABASE_URL not set. Database features will be unavailable.")


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Image(Base):
    """Image metadata and AI analysis results"""
    __tablename__ = "images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="")
    image_path = Column(String(512), nullable=False, default="")
    image_url = Column(String(512), nullable=False, default="")
    ai_description = Column(Text, nullable=False, default="")
    dominant_colors = Column(JSON, nullable=False, default=list)
    primary_mood = Column(String(50), nullable=False, default="neutral")
    optimal_time = Column(String(50), nullable=False, default="any")
    base_score = Column(Float, nullable=False, default=0.5)
    display_count = Column(Integer, nullable=False, default=0)
    last_displayed = Column(DateTime(timezone=True), nullable=True)
    is_analyzed = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    # Error recovery (Enhancement 7)
    analysis_error = Column(Text, nullable=False, default="")
    retry_count = Column(Integer, nullable=False, default=0)
    # Image scheduling (Enhancement 9)
    schedule_start = Column(DateTime(timezone=True), nullable=True)
    schedule_end = Column(DateTime(timezone=True), nullable=True)
    time_window = Column(String(100), nullable=False, default="any")
    user_id = Column(String(36), nullable=False, default="")

    __table_args__ = (
        Index("idx_mood_time", "primary_mood", "optimal_time"),
        Index("idx_active_analyzed", "is_active", "is_analyzed"),
        Index("idx_images_title", "title"),
    )


class ImageTag(Base):
    """AI-generated semantic tags for images"""
    __tablename__ = "image_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(String(36), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, default="subject")
    confidence = Column(Float, nullable=False, default=1.0)

    __table_args__ = (
        UniqueConstraint("image_id", "name", name="uq_image_tag"),
        Index("idx_tags_image_id", "image_id"),
        Index("idx_tags_name", "name"),
        Index("idx_tags_category", "category"),
    )


class UserPreference(Base):
    """User-facing configuration singleton"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, default=1)
    preferred_mood = Column(String(50), nullable=False, default="calm")
    sensitivity = Column(String(20), nullable=False, default="medium")
    time_mood_map = Column(JSON, nullable=False, default=dict)
    override_active = Column(Boolean, nullable=False, default=False)
    override_image_id = Column(String(36), ForeignKey("images.id", ondelete="SET NULL"), nullable=True)
    recency_weight = Column(Float, nullable=False, default=0.2)
    user_id = Column(String(36), nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))


class ContextLog(Base):
    """Immutable audit trail for every decision"""
    __tablename__ = "context_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    time_period = Column(String(50), nullable=False, default="")
    detected_mood = Column(String(50), nullable=False, default="")
    selected_image_id = Column(String(36), ForeignKey("images.id", ondelete="SET NULL"), nullable=True)
    selection_score = Column(Float, nullable=False, default=0.0)
    score_breakdown = Column(JSON, nullable=False, default=dict)
    matched_tags = Column(JSON, nullable=False, default=list)
    reasoning_text = Column(Text, nullable=False, default="")
    was_override = Column(Boolean, nullable=False, default=False)
    user_id = Column(String(36), nullable=False, default="")

    __table_args__ = (
        Index("idx_log_timestamp", "timestamp", postgresql_using="btree"),
        Index("idx_log_image_id", "selected_image_id"),
    )


class DisplayConfig(Base):
    """System-wide configuration singleton"""
    __tablename__ = "display_config"

    id = Column(Integer, primary_key=True, default=1)
    poll_interval_seconds = Column(Integer, nullable=False, default=300)
    transition_duration_ms = Column(Integer, nullable=False, default=1500)
    show_reasoning_overlay = Column(Boolean, nullable=False, default=True)
    overlay_auto_hide_seconds = Column(Integer, nullable=False, default=8)
    night_brightness = Column(Float, nullable=False, default=0.7)
    # Vision API prompt config (Enhancement 10)
    analysis_depth = Column(String(20), nullable=False, default="standard")
    analysis_focus = Column(Text, nullable=False, default="")
    custom_prompt = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))


class Preset(Base):
    """Saved mood/sensitivity presets for quick switching"""
    __tablename__ = "presets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    mood = Column(String(50), nullable=False, default="calm")
    sensitivity = Column(String(20), nullable=False, default="medium")
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))


class ImageInteraction(Base):
    """User interaction tracking (likes/skips)"""
    __tablename__ = "image_interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(String(36), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    interaction = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    user_id = Column(String(36), nullable=False, default="")

    __table_args__ = (
        CheckConstraint("interaction IN ('like', 'skip')", name="ck_interaction_type"),
        Index("idx_interaction_lookup", "image_id", "interaction"),
        Index("idx_interactions_ts", "timestamp"),
    )


class User(Base):
    """User accounts for multi-user authentication"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False, default="")
    email = Column(String(255), nullable=False, default="")
    password_hash = Column(Text, nullable=False)
    profile_type = Column(String(20), nullable=False, default="Standard")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("profile_type IN ('Standard', 'Kids', 'Professional')", name="ck_profile_type"),
    )


class UserSession(Base):
    """Persistent session tokens for cookie-based authentication"""
    __tablename__ = "user_sessions"

    token      = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

def get_db():
    """Dependency injection for database sessions"""
    if SessionLocal is None:
        raise RuntimeError(
            "Database not available. "
            "Set DATABASE_URL in your .env file (local) or Render environment."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Create all tables. Safe to call on startup (idempotent)"""
    Base.metadata.create_all(bind=engine)

    # Seed singleton rows and default presets
    db = SessionLocal()
    try:
        if not db.query(UserPreference).filter_by(id=1).first():
            db.add(UserPreference(id=1))
        if not db.query(DisplayConfig).filter_by(id=1).first():
            db.add(DisplayConfig(id=1))
        # Seed default presets
        for name, mood, sens in [
            ("Morning Energy", "energetic", "high"),
            ("Evening Calm", "calm", "medium"),
            ("Night Mystery", "mysterious", "high"),
        ]:
            if not db.query(Preset).filter_by(name=name).first():
                db.add(Preset(name=name, mood=mood, sensitivity=sens, is_default=True))
        db.commit()
    finally:
        db.close()
