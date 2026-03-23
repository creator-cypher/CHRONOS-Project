"""
Chronos — Database Query Layer (PostgreSQL)
=============================================

All SQL read/write operations live here. Views and logic modules import
from this module exclusively — they never write raw SQL themselves.
This mirrors the Repository pattern and uses SQLAlchemy ORM for PostgreSQL.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, or_, and_, case, Integer, text

# Use SQLAlchemy ORM for PostgreSQL
from .postgres_schema import (
    SessionLocal, Image, ImageTag, ContextLog, ImageInteraction,
    DisplayConfig, Preset, User, UserPreference
)

# Helper to check if database is available
def _check_db():
    if SessionLocal is None:
        raise RuntimeError(
            "Database not available. "
            "Check that DATABASE_URL is set in environment variables."
        )


# ---------------------------------------------------------------------------
# Users (Authentication)
# ---------------------------------------------------------------------------

def create_user(
    username: str, password_hash: str, name: str = "",
    email: str = "", profile_type: str = "Standard",
) -> str:
    """Creates a new user and returns the user ID."""
    user_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        user = User(
            id=user_id,
            username=username,
            name=name or username,
            email=email,
            password_hash=password_hash,
            profile_type=profile_type,
        )
        session.add(user)
        session.commit()
    finally:
        session.close()
    return user_id


def get_user_by_username(username: str) -> Optional[dict]:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "password_hash": user.password_hash,
                "profile_type": user.profile_type,
            }
        return None
    finally:
        session.close()


def get_user_by_id(user_id: str) -> Optional[dict]:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "email": user.email,
                "password_hash": user.password_hash,
                "profile_type": user.profile_type,
            }
        return None
    finally:
        session.close()


def get_all_users() -> list[dict]:
    session = SessionLocal()
    try:
        users = session.query(User).order_by(User.created_at.desc()).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "name": u.name,
                "email": u.email,
                "password_hash": u.password_hash,
                "profile_type": u.profile_type,
            }
            for u in users
        ]
    finally:
        session.close()


def username_exists(username: str) -> bool:
    session = SessionLocal()
    try:
        exists = session.query(User).filter(User.username == username).first() is not None
        return exists
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def get_all_images(active_only: bool = True, user_id: str = "") -> list[dict]:
    """Returns all images, optionally filtered to active ones and/or a specific user."""
    session = SessionLocal()
    try:
        query = session.query(Image)
        if active_only:
            query = query.filter(Image.is_active == True)
        if user_id:
            query = query.filter(Image.user_id == user_id)
        images = query.order_by(Image.uploaded_at.desc()).all()
        return [
            {
                "id": img.id,
                "title": img.title,
                "image_path": img.image_path,
                "image_url": img.image_url,
                "ai_description": img.ai_description,
                "dominant_colors": img.dominant_colors,
                "primary_mood": img.primary_mood,
                "optimal_time": img.optimal_time,
                "base_score": img.base_score,
                "display_count": img.display_count,
                "last_displayed": img.last_displayed,
                "is_analyzed": img.is_analyzed,
                "is_active": img.is_active,
                "uploaded_at": img.uploaded_at,
                "analysis_error": img.analysis_error,
                "retry_count": img.retry_count,
                "schedule_start": img.schedule_start,
                "schedule_end": img.schedule_end,
                "time_window": img.time_window,
                "user_id": img.user_id,
            }
            for img in images
        ]
    finally:
        session.close()


def get_analyzed_images(user_id: str = "") -> list[dict]:
    """
    Returns images that have been processed by the Vision API.
    These are the only candidates for the Decision Engine.
    """
    session = SessionLocal()
    try:
        query = session.query(Image).filter(
            and_(Image.is_active == True, Image.is_analyzed == True)
        )
        if user_id:
            query = query.filter(Image.user_id == user_id)
        images = query.order_by(Image.last_displayed.asc()).all()
        return [
            {
                "id": img.id,
                "title": img.title,
                "image_path": img.image_path,
                "image_url": img.image_url,
                "ai_description": img.ai_description,
                "dominant_colors": img.dominant_colors,
                "primary_mood": img.primary_mood,
                "optimal_time": img.optimal_time,
                "base_score": img.base_score,
                "display_count": img.display_count,
                "last_displayed": img.last_displayed,
                "is_analyzed": img.is_analyzed,
                "is_active": img.is_active,
                "uploaded_at": img.uploaded_at,
                "analysis_error": img.analysis_error,
                "retry_count": img.retry_count,
                "schedule_start": img.schedule_start,
                "schedule_end": img.schedule_end,
                "time_window": img.time_window,
                "user_id": img.user_id,
            }
            for img in images
        ]
    finally:
        session.close()


def get_image_by_id(image_id: str) -> Optional[dict]:
    session = SessionLocal()
    try:
        img = session.query(Image).filter(Image.id == image_id).first()
        if img:
            return {
                "id": img.id,
                "title": img.title,
                "image_path": img.image_path,
                "image_url": img.image_url,
                "ai_description": img.ai_description,
                "dominant_colors": img.dominant_colors,
                "primary_mood": img.primary_mood,
                "optimal_time": img.optimal_time,
                "base_score": img.base_score,
                "display_count": img.display_count,
                "last_displayed": img.last_displayed,
                "is_analyzed": img.is_analyzed,
                "is_active": img.is_active,
                "uploaded_at": img.uploaded_at,
                "analysis_error": img.analysis_error,
                "retry_count": img.retry_count,
                "schedule_start": img.schedule_start,
                "schedule_end": img.schedule_end,
                "time_window": img.time_window,
                "user_id": img.user_id,
            }
        return None
    finally:
        session.close()


def add_image(title: str, image_path: str = "", image_url: str = "", user_id: str = "") -> str:
    """
    Inserts a new image record. Returns the new UUID.
    The image is marked is_analyzed=0 until Vision API processes it.
    """
    image_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        image = Image(
            id=image_id,
            title=title,
            image_path=image_path,
            image_url=image_url,
            user_id=user_id,
        )
        session.add(image)
        session.commit()
    finally:
        session.close()
    return image_id


def update_image_analysis(
    image_id: str,
    description: str,
    primary_mood: str,
    optimal_time: str,
    base_score: float,
    dominant_colors: list,
    tags: list[dict],
) -> None:
    """
    Writes AI-generated metadata to an image record and replaces its tags.
    Called exclusively by services/vision.py after a successful API call.
    """
    session = SessionLocal()
    try:
        # Update image record
        image = session.query(Image).filter(Image.id == image_id).first()
        if image:
            image.ai_description = description
            image.primary_mood = primary_mood
            image.optimal_time = optimal_time
            image.base_score = base_score
            image.dominant_colors = dominant_colors
            image.is_analyzed = True
            session.commit()

        # Delete existing tags
        session.query(ImageTag).filter(ImageTag.image_id == image_id).delete()
        session.commit()

        # Insert new tags
        for tag in tags:
            image_tag = ImageTag(
                image_id=image_id,
                name=tag["name"],
                category=tag["category"],
                confidence=tag["confidence"],
            )
            session.add(image_tag)
        session.commit()
    finally:
        session.close()


def update_image_display_stats(image_id: str) -> None:
    """Increments display counter and sets last_displayed timestamp."""
    session = SessionLocal()
    try:
        image = session.query(Image).filter(Image.id == image_id).first()
        if image:
            image.display_count = (image.display_count or 0) + 1
            image.last_displayed = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


def deactivate_image(image_id: str) -> None:
    """Soft-delete — preserves the record for historical log integrity."""
    session = SessionLocal()
    try:
        image = session.query(Image).filter(Image.id == image_id).first()
        if image:
            image.is_active = False
            session.commit()
    finally:
        session.close()


def get_tags_for_image(image_id: str) -> list[dict]:
    session = SessionLocal()
    try:
        tags = session.query(ImageTag).filter(
            ImageTag.image_id == image_id
        ).order_by(ImageTag.confidence.desc()).all()
        return [
            {
                "id": tag.id,
                "image_id": tag.image_id,
                "name": tag.name,
                "category": tag.category,
                "confidence": tag.confidence,
            }
            for tag in tags
        ]
    finally:
        session.close()


def search_images(
    text: str = "",
    mood: str = "",
    time_period: str = "",
    active_only: bool = True,
    user_id: str = "",
) -> list[dict]:
    """Search images by title/tags, mood, and time period."""
    session = SessionLocal()
    try:
        query = session.query(Image)

        if active_only:
            query = query.filter(Image.is_active == True)

        if user_id:
            query = query.filter(Image.user_id == user_id)

        if mood:
            query = query.filter(Image.primary_mood == mood)

        if time_period:
            query = query.filter(Image.optimal_time == time_period)

        if text:
            # Search by title or tags
            like_text = f"%{text}%"
            query = query.filter(
                or_(
                    Image.title.ilike(like_text),
                    Image.id.in_(
                        session.query(ImageTag.image_id).filter(
                            ImageTag.name.ilike(like_text)
                        )
                    )
                )
            )

        images = query.order_by(Image.uploaded_at.desc()).all()
        return [
            {
                "id": img.id,
                "title": img.title,
                "image_path": img.image_path,
                "image_url": img.image_url,
                "ai_description": img.ai_description,
                "dominant_colors": img.dominant_colors,
                "primary_mood": img.primary_mood,
                "optimal_time": img.optimal_time,
                "base_score": img.base_score,
                "display_count": img.display_count,
                "last_displayed": img.last_displayed,
                "is_analyzed": img.is_analyzed,
                "is_active": img.is_active,
                "uploaded_at": img.uploaded_at,
                "analysis_error": img.analysis_error,
                "retry_count": img.retry_count,
                "schedule_start": img.schedule_start,
                "schedule_end": img.schedule_end,
                "time_window": img.time_window,
                "user_id": img.user_id,
            }
            for img in images
        ]
    finally:
        session.close()


def deactivate_images(image_ids: list[str]) -> int:
    """Soft-delete multiple images. Returns count affected."""
    if not image_ids:
        return 0
    session = SessionLocal()
    try:
        count = session.query(Image).filter(Image.id.in_(image_ids)).update(
            {Image.is_active: False}
        )
        session.commit()
        return count
    finally:
        session.close()


def get_image_interaction_summary(user_id: str = "") -> list[dict]:
    """Aggregated likes/skips per image for analytics."""
    session = SessionLocal()
    try:
        # Aggregate interactions by type
        query = session.query(
            Image.id,
            Image.title,
            Image.primary_mood,
            func.coalesce(
                func.sum(case((ImageInteraction.interaction == 'like', 1), else_=0)),
                0
            ).label('likes'),
            func.coalesce(
                func.sum(case((ImageInteraction.interaction == 'skip', 1), else_=0)),
                0
            ).label('skips'),
        ).outerjoin(
            ImageInteraction,
            Image.id == ImageInteraction.image_id
        ).filter(Image.is_active == True)

        if user_id:
            query = query.filter(Image.user_id == user_id)

        results = query.group_by(Image.id, Image.title, Image.primary_mood).order_by(
            func.coalesce(
                func.sum(case((ImageInteraction.interaction == 'like', 1), else_=0)),
                0
            ).desc()
        ).all()

        return [
            {
                "id": r[0],
                "title": r[1],
                "primary_mood": r[2],
                "likes": r[3],
                "skips": r[4],
            }
            for r in results
        ]
    finally:
        session.close()


def get_mood_distribution() -> list[dict]:
    """Count of active images per mood category."""
    session = SessionLocal()
    try:
        results = session.query(
            Image.primary_mood,
            func.count(Image.id).label('count')
        ).filter(Image.is_active == True).group_by(Image.primary_mood).order_by(
            func.count(Image.id).desc()
        ).all()

        return [
            {
                "primary_mood": r[0],
                "count": r[1],
            }
            for r in results
        ]
    finally:
        session.close()


def get_hourly_usage() -> list[dict]:
    """Hourly distribution of display decisions from context_logs."""
    session = SessionLocal()
    try:
        results = session.query(
            func.extract('hour', ContextLog.timestamp).label('hour'),
            func.count(ContextLog.id).label('count')
        ).group_by(
            func.extract('hour', ContextLog.timestamp)
        ).order_by(
            func.extract('hour', ContextLog.timestamp)
        ).all()

        return [
            {
                "hour": int(r[0]) if r[0] is not None else 0,
                "count": r[1],
            }
            for r in results
        ]
    finally:
        session.close()


def get_mood_over_time(days: int = 30) -> list[dict]:
    """Daily mood distribution from context_logs for the last N days."""
    session = SessionLocal()
    try:
        from sqlalchemy import cast
        from sqlalchemy.types import Date

        results = session.query(
            cast(ContextLog.timestamp, Date).label('date'),
            ContextLog.detected_mood,
            func.count(ContextLog.id).label('count')
        ).filter(
            ContextLog.timestamp >= func.current_timestamp() - text(f"interval '{days} days'")
        ).group_by(
            cast(ContextLog.timestamp, Date),
            ContextLog.detected_mood
        ).order_by(
            cast(ContextLog.timestamp, Date)
        ).all()

        return [
            {
                "date": r[0],
                "mood": r[1],
                "count": r[2],
            }
            for r in results
        ]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# User Preferences
# ---------------------------------------------------------------------------

def get_preferences(user_id: str = "") -> dict:
    """Retrieves user preferences — per-user if user_id is set, otherwise singleton."""
    session = SessionLocal()
    try:
        if user_id:
            pref = session.query(UserPreference).filter(UserPreference.user_id == user_id).first()
            if not pref:
                try:
                    # Create per-user preferences row
                    pref = UserPreference(user_id=user_id)
                    session.add(pref)
                    session.commit()
                except Exception:
                    session.rollback()
                    # Row already exists — just fetch it
                    pref = session.query(UserPreference).filter(
                        UserPreference.user_id == user_id
                    ).first()
                    if not pref:
                        return {}
        else:
            pref = session.query(UserPreference).first()

        if not pref:
            return {}

        data = {
            "id": pref.id,
            "preferred_mood": pref.preferred_mood,
            "sensitivity": pref.sensitivity,
            "time_mood_map": pref.time_mood_map or {},
            "override_active": pref.override_active,
            "override_image_id": pref.override_image_id,
            "recency_weight": pref.recency_weight,
            "user_id": pref.user_id,
            "updated_at": pref.updated_at,
        }
        return data
    finally:
        session.close()


def update_preferences(user_id: str = "", **kwargs) -> None:
    """
    Updates any subset of preference fields.
    Accepted keys: preferred_mood, sensitivity, time_mood_map,
                   override_active, override_image_id, recency_weight.
    """
    if not kwargs:
        return

    session = SessionLocal()
    try:
        if user_id:
            # Ensure per-user row exists
            pref = session.query(UserPreference).filter(UserPreference.user_id == user_id).first()
            if not pref:
                try:
                    pref = UserPreference(user_id=user_id)
                    session.add(pref)
                    session.commit()
                    pref = session.query(UserPreference).filter(UserPreference.user_id == user_id).first()
                except Exception:
                    # If creation fails, just retrieve what's there
                    session.rollback()
                    pref = session.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        else:
            pref = session.query(UserPreference).filter(UserPreference.id == 1).first()

        if pref:
            for key, value in kwargs.items():
                if hasattr(pref, key):
                    setattr(pref, key, value)
            pref.updated_at = datetime.now(timezone.utc)
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Context Logs
# ---------------------------------------------------------------------------

def save_context_log(
    time_period: str,
    detected_mood: str,
    image_id: Optional[str],
    selection_score: float,
    score_breakdown: dict,
    matched_tags: list,
    reasoning_text: str,
    was_override: bool = False,
    user_id: str = "",
) -> None:
    """
    Writes an immutable audit record for every display decision.
    This feeds the Reasoning Overlay and the history panel.
    """
    session = SessionLocal()
    try:
        log = ContextLog(
            time_period=time_period,
            detected_mood=detected_mood,
            selected_image_id=image_id,
            selection_score=selection_score,
            score_breakdown=score_breakdown,
            matched_tags=matched_tags,
            reasoning_text=reasoning_text,
            was_override=was_override,
            user_id=user_id,
        )
        session.add(log)
        session.commit()
    finally:
        session.close()


def get_recent_logs(limit: int = 10, user_id: str = "") -> list[dict]:
    """Returns the most recent display decisions for the history panel."""
    session = SessionLocal()
    try:
        query = session.query(ContextLog).outerjoin(
            Image,
            ContextLog.selected_image_id == Image.id
        )

        if user_id:
            query = query.filter(ContextLog.user_id == user_id)

        logs = query.order_by(ContextLog.timestamp.desc()).limit(limit).all()

        result = []
        for log in logs:
            image_title = ""
            image_mood = ""
            if log.selected_image_id:
                img = session.query(Image).filter(Image.id == log.selected_image_id).first()
                if img:
                    image_title = img.title
                    image_mood = img.primary_mood

            d = {
                "id": log.id,
                "timestamp": log.timestamp,
                "time_period": log.time_period,
                "detected_mood": log.detected_mood,
                "selected_image_id": log.selected_image_id,
                "selection_score": log.selection_score,
                "score_breakdown": log.score_breakdown or {},
                "matched_tags": log.matched_tags or [],
                "reasoning_text": log.reasoning_text,
                "was_override": log.was_override,
                "user_id": log.user_id,
                "image_title": image_title,
                "image_mood": image_mood,
            }
            result.append(d)

        return result
    finally:
        session.close()


def get_recently_shown_ids(window_minutes: int = 60) -> set:
    """Returns image IDs displayed within the recency window (for penalty logic)."""
    from sqlalchemy import func as sql_func
    from datetime import timedelta

    session = SessionLocal()
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        rows = session.query(ContextLog.selected_image_id).filter(
            and_(
                ContextLog.timestamp >= cutoff_time,
                ContextLog.selected_image_id != None
            )
        ).all()
        return {r[0] for r in rows if r[0]}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Image Interactions (Like / Skip)
# ---------------------------------------------------------------------------

def save_interaction(image_id: str, interaction: str, user_id: str = "") -> None:
    """Record a user like or skip for an image. Feeds the scoring engine."""
    session = SessionLocal()
    try:
        interaction_record = ImageInteraction(
            image_id=image_id,
            interaction=interaction,
            user_id=user_id,
        )
        session.add(interaction_record)
        session.commit()
    finally:
        session.close()


def get_interaction_counts(image_id: str) -> dict:
    """Returns {'like': n, 'skip': n} for a given image."""
    session = SessionLocal()
    try:
        results = session.query(
            ImageInteraction.interaction,
            func.count(ImageInteraction.id).label('cnt')
        ).filter(
            ImageInteraction.image_id == image_id
        ).group_by(ImageInteraction.interaction).all()

        counts = {"like": 0, "skip": 0}
        for row in results:
            if row[0] in counts:
                counts[row[0]] = row[1]
        return counts
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Display Config
# ---------------------------------------------------------------------------

def get_display_config() -> dict:
    """Retrieves the singleton display configuration."""
    session = SessionLocal()
    try:
        config = session.query(DisplayConfig).filter(DisplayConfig.id == 1).first()
        if config:
            return {
                "id": config.id,
                "poll_interval_seconds": config.poll_interval_seconds,
                "transition_duration_ms": config.transition_duration_ms,
                "show_reasoning_overlay": config.show_reasoning_overlay,
                "overlay_auto_hide_seconds": config.overlay_auto_hide_seconds,
                "night_brightness": config.night_brightness,
                "analysis_depth": config.analysis_depth,
                "analysis_focus": config.analysis_focus,
                "custom_prompt": config.custom_prompt,
                "updated_at": config.updated_at,
            }
        return {}
    finally:
        session.close()


def update_display_config(**kwargs) -> None:
    """Updates any subset of display_config fields."""
    if not kwargs:
        return

    session = SessionLocal()
    try:
        config = session.query(DisplayConfig).filter(DisplayConfig.id == 1).first()
        if config:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            config.updated_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

def get_presets() -> list[dict]:
    """Returns all saved mood/sensitivity presets."""
    session = SessionLocal()
    try:
        presets = session.query(Preset).order_by(
            Preset.is_default.desc(),
            Preset.name.asc()
        ).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "mood": p.mood,
                "sensitivity": p.sensitivity,
                "is_default": p.is_default,
                "created_at": p.created_at,
            }
            for p in presets
        ]
    finally:
        session.close()


def save_preset(name: str, mood: str, sensitivity: str) -> int:
    """Creates a new preset. Returns the new ID."""
    session = SessionLocal()
    try:
        preset = Preset(
            name=name,
            mood=mood,
            sensitivity=sensitivity,
        )
        session.add(preset)
        session.commit()
        session.refresh(preset)
        return preset.id
    finally:
        session.close()


def delete_preset(preset_id: int) -> None:
    session = SessionLocal()
    try:
        session.query(Preset).filter(Preset.id == preset_id).delete()
        session.commit()
    finally:
        session.close()


def apply_preset(preset_id: int) -> None:
    """Loads preset values into user_preferences."""
    session = SessionLocal()
    try:
        preset = session.query(Preset).filter(Preset.id == preset_id).first()
        if preset:
            pref = session.query(UserPreference).filter(UserPreference.id == 1).first()
            if pref:
                pref.preferred_mood = preset.mood
                pref.sensitivity = preset.sensitivity
                pref.updated_at = datetime.now(timezone.utc)
                session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Error Recovery
# ---------------------------------------------------------------------------

def update_image_error(image_id: str, error: str, retry_count: int) -> None:
    """Records an analysis failure on an image."""
    session = SessionLocal()
    try:
        image = session.query(Image).filter(Image.id == image_id).first()
        if image:
            image.analysis_error = error
            image.retry_count = retry_count
            session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Image Scheduling
# ---------------------------------------------------------------------------

def get_scheduled_images(current_date: str = "", current_period: str = "", user_id: str = "") -> list[dict]:
    """
    Returns analyzed, active images that are within their schedule window.
    Falls back to get_analyzed_images() behaviour when no scheduling columns exist.
    """
    session = SessionLocal()
    try:
        query = session.query(Image).filter(
            and_(Image.is_active == True, Image.is_analyzed == True)
        )

        if user_id:
            query = query.filter(Image.user_id == user_id)

        if current_date:
            # Date constraints
            query = query.filter(
                and_(
                    or_(Image.schedule_start == None, Image.schedule_start <= current_date),
                    or_(Image.schedule_end == None, Image.schedule_end >= current_date)
                )
            )

        if current_period:
            # Time period constraints
            query = query.filter(
                or_(
                    Image.time_window == 'any',
                    Image.time_window.ilike(f'%{current_period}%')
                )
            )

        images = query.order_by(Image.last_displayed.asc()).all()

        return [
            {
                "id": img.id,
                "title": img.title,
                "image_path": img.image_path,
                "image_url": img.image_url,
                "ai_description": img.ai_description,
                "dominant_colors": img.dominant_colors,
                "primary_mood": img.primary_mood,
                "optimal_time": img.optimal_time,
                "base_score": img.base_score,
                "display_count": img.display_count,
                "last_displayed": img.last_displayed,
                "is_analyzed": img.is_analyzed,
                "is_active": img.is_active,
                "uploaded_at": img.uploaded_at,
                "analysis_error": img.analysis_error,
                "retry_count": img.retry_count,
                "schedule_start": img.schedule_start,
                "schedule_end": img.schedule_end,
                "time_window": img.time_window,
                "user_id": img.user_id,
            }
            for img in images
        ]
    finally:
        session.close()


def update_image_schedule(
    image_id: str, schedule_start: str, schedule_end: str, time_window: str
) -> None:
    """Sets scheduling constraints on an image."""
    session = SessionLocal()
    try:
        image = session.query(Image).filter(Image.id == image_id).first()
        if image:
            image.schedule_start = schedule_start or None
            image.schedule_end = schedule_end or None
            image.time_window = time_window
            session.commit()
    finally:
        session.close()
