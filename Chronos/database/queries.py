"""
Chronos — Database Query Layer
================================

All SQL read/write operations live here. Views and logic modules import
from this module exclusively — they never write raw SQL themselves.
This mirrors the Repository pattern and makes the database easy to swap.

Every function opens its own connection and closes it on return.
For a single-process Streamlit app, connection pooling is unnecessary.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .schema import get_connection


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def get_all_images(active_only: bool = True) -> list[dict]:
    """Returns all images, optionally filtered to active ones only."""
    conn = get_connection()
    sql  = "SELECT * FROM images"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY uploaded_at DESC"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_analyzed_images() -> list[dict]:
    """
    Returns images that have been processed by the Vision API.
    These are the only candidates for the Decision Engine.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM images WHERE is_active = 1 AND is_analyzed = 1 "
        "ORDER BY last_displayed ASC NULLS FIRST"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_image_by_id(image_id: str) -> Optional[dict]:
    conn = get_connection()
    row  = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_image(title: str, image_path: str = "", image_url: str = "") -> str:
    """
    Inserts a new image record. Returns the new UUID.
    The image is marked is_analyzed=0 until Vision API processes it.
    """
    image_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        """INSERT INTO images (id, title, image_path, image_url)
           VALUES (?, ?, ?, ?)""",
        (image_id, title, image_path, image_url),
    )
    conn.commit()
    conn.close()
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
    conn = get_connection()

    conn.execute(
        """UPDATE images
           SET ai_description = ?, primary_mood = ?, optimal_time = ?,
               base_score = ?, dominant_colors = ?, is_analyzed = 1
           WHERE id = ?""",
        (description, primary_mood, optimal_time, base_score,
         json.dumps(dominant_colors), image_id),
    )

    # Replace existing tags
    conn.execute("DELETE FROM image_tags WHERE image_id = ?", (image_id,))
    conn.executemany(
        "INSERT OR IGNORE INTO image_tags (image_id, name, category, confidence) VALUES (?,?,?,?)",
        [(image_id, t["name"], t["category"], t["confidence"]) for t in tags],
    )

    conn.commit()
    conn.close()


def update_image_display_stats(image_id: str) -> None:
    """Increments display counter and sets last_displayed timestamp."""
    conn = get_connection()
    conn.execute(
        """UPDATE images
           SET display_count = display_count + 1,
               last_displayed = datetime('now')
           WHERE id = ?""",
        (image_id,),
    )
    conn.commit()
    conn.close()


def deactivate_image(image_id: str) -> None:
    """Soft-delete — preserves the record for historical log integrity."""
    conn = get_connection()
    conn.execute("UPDATE images SET is_active = 0 WHERE id = ?", (image_id,))
    conn.commit()
    conn.close()


def get_tags_for_image(image_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM image_tags WHERE image_id = ? ORDER BY confidence DESC",
        (image_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_images(
    text: str = "",
    mood: str = "",
    time_period: str = "",
    active_only: bool = True,
) -> list[dict]:
    """Search images by title/tags, mood, and time period."""
    conn = get_connection()
    conditions = []
    params: list = []

    if active_only:
        conditions.append("i.is_active = 1")

    if mood:
        conditions.append("i.primary_mood = ?")
        params.append(mood)

    if time_period:
        conditions.append("i.optimal_time = ?")
        params.append(time_period)

    if text:
        conditions.append(
            "(i.title LIKE ? OR EXISTS "
            "(SELECT 1 FROM image_tags t WHERE t.image_id = i.id AND t.name LIKE ?))"
        )
        like = f"%{text}%"
        params.extend([like, like])

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT DISTINCT i.* FROM images i{where} ORDER BY i.uploaded_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deactivate_images(image_ids: list[str]) -> int:
    """Soft-delete multiple images. Returns count affected."""
    if not image_ids:
        return 0
    conn = get_connection()
    placeholders = ",".join("?" for _ in image_ids)
    cur = conn.execute(
        f"UPDATE images SET is_active = 0 WHERE id IN ({placeholders})", image_ids
    )
    conn.commit()
    count = cur.rowcount
    conn.close()
    return count


def get_image_interaction_summary() -> list[dict]:
    """Aggregated likes/skips per image for analytics."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT i.id, i.title, i.primary_mood,
                  COALESCE(SUM(CASE WHEN ia.interaction = 'like' THEN 1 ELSE 0 END), 0) as likes,
                  COALESCE(SUM(CASE WHEN ia.interaction = 'skip' THEN 1 ELSE 0 END), 0) as skips
           FROM images i
           LEFT JOIN image_interactions ia ON ia.image_id = i.id
           WHERE i.is_active = 1
           GROUP BY i.id, i.title, i.primary_mood
           ORDER BY likes DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mood_distribution() -> list[dict]:
    """Count of active images per mood category."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT primary_mood, COUNT(*) as count FROM images "
        "WHERE is_active = 1 GROUP BY primary_mood ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_hourly_usage() -> list[dict]:
    """Hourly distribution of display decisions from context_logs."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
           FROM context_logs GROUP BY hour ORDER BY hour"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mood_over_time(days: int = 30) -> list[dict]:
    """Daily mood distribution from context_logs for the last N days."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT date(timestamp) as date, detected_mood as mood, COUNT(*) as count
           FROM context_logs
           WHERE timestamp >= datetime('now', ? || ' days')
           GROUP BY date, mood ORDER BY date""",
        (f"-{days}",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_images(limit: int = 10) -> list[dict]:
    """Most displayed images with interaction stats."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT i.id, i.title, i.primary_mood, i.display_count, i.image_url,
                  COALESCE(SUM(CASE WHEN ia.interaction = 'like' THEN 1 ELSE 0 END), 0) as likes,
                  COALESCE(SUM(CASE WHEN ia.interaction = 'skip' THEN 1 ELSE 0 END), 0) as skips
           FROM images i
           LEFT JOIN image_interactions ia ON ia.image_id = i.id
           WHERE i.is_active = 1
           GROUP BY i.id, i.title, i.primary_mood, i.display_count, i.image_url
           ORDER BY i.display_count DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# User Preferences
# ---------------------------------------------------------------------------

def get_preferences() -> dict:
    """Retrieves the singleton user preferences record."""
    conn = get_connection()
    row  = conn.execute("SELECT * FROM user_preferences WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return {}
    data = dict(row)
    data["time_mood_map"] = json.loads(data.get("time_mood_map") or "{}")
    return data


def update_preferences(**kwargs) -> None:
    """
    Updates any subset of preference fields.
    Accepted keys: preferred_mood, sensitivity, time_mood_map,
                   override_active, override_image_id, recency_weight.
    """
    if not kwargs:
        return

    # Serialize time_mood_map if present
    if "time_mood_map" in kwargs:
        kwargs["time_mood_map"] = json.dumps(kwargs["time_mood_map"])

    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [1]

    conn = get_connection()
    conn.execute(
        f"UPDATE user_preferences SET {fields}, updated_at = datetime('now') WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


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
) -> None:
    """
    Writes an immutable audit record for every display decision.
    This feeds the Reasoning Overlay and the history panel.
    """
    conn = get_connection()
    conn.execute(
        """INSERT INTO context_logs
           (time_period, detected_mood, selected_image_id, selection_score,
            score_breakdown, matched_tags, reasoning_text, was_override)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            time_period, detected_mood, image_id, selection_score,
            json.dumps(score_breakdown), json.dumps(matched_tags),
            reasoning_text, int(was_override),
        ),
    )
    conn.commit()
    conn.close()


def get_recent_logs(limit: int = 10) -> list[dict]:
    """Returns the most recent display decisions for the history panel."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT l.*, i.title as image_title, i.primary_mood
           FROM context_logs l
           LEFT JOIN images i ON l.selected_image_id = i.id
           ORDER BY l.timestamp DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["score_breakdown"] = json.loads(d.get("score_breakdown") or "{}")
        d["matched_tags"]    = json.loads(d.get("matched_tags")    or "[]")
        result.append(d)
    return result


def get_recently_shown_ids(window_minutes: int = 60) -> set:
    """Returns image IDs displayed within the recency window (for penalty logic)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT selected_image_id FROM context_logs
           WHERE timestamp >= datetime('now', ? || ' minutes')
           AND selected_image_id IS NOT NULL""",
        (f"-{window_minutes}",),
    ).fetchall()
    conn.close()
    return {r["selected_image_id"] for r in rows}


# ---------------------------------------------------------------------------
# Image Interactions (Like / Skip)
# ---------------------------------------------------------------------------

def save_interaction(image_id: str, interaction: str) -> None:
    """Record a user like or skip for an image. Feeds the scoring engine."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO image_interactions (image_id, interaction) VALUES (?, ?)",
        (image_id, interaction),
    )
    conn.commit()
    conn.close()


def get_interaction_counts(image_id: str) -> dict:
    """Returns {'like': n, 'skip': n} for a given image."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT interaction, COUNT(*) as cnt FROM image_interactions "
        "WHERE image_id = ? GROUP BY interaction",
        (image_id,),
    ).fetchall()
    conn.close()
    counts = {"like": 0, "skip": 0}
    for row in rows:
        counts[row["interaction"]] = row["cnt"]
    return counts


# ---------------------------------------------------------------------------
# Display Config
# ---------------------------------------------------------------------------

def get_display_config() -> dict:
    """Retrieves the singleton display configuration."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM display_config WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}


def update_display_config(**kwargs) -> None:
    """Updates any subset of display_config fields."""
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [1]
    conn = get_connection()
    conn.execute(
        f"UPDATE display_config SET {fields}, updated_at = datetime('now') WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

def get_presets() -> list[dict]:
    """Returns all saved mood/sensitivity presets."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM presets ORDER BY is_default DESC, name ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_preset(name: str, mood: str, sensitivity: str) -> int:
    """Creates a new preset. Returns the new ID."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO presets (name, mood, sensitivity) VALUES (?, ?, ?)",
        (name, mood, sensitivity),
    )
    conn.commit()
    preset_id = cur.lastrowid
    conn.close()
    return preset_id


def delete_preset(preset_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
    conn.commit()
    conn.close()


def apply_preset(preset_id: int) -> None:
    """Loads preset values into user_preferences."""
    conn = get_connection()
    row = conn.execute("SELECT mood, sensitivity FROM presets WHERE id = ?", (preset_id,)).fetchone()
    if row:
        conn.execute(
            "UPDATE user_preferences SET preferred_mood = ?, sensitivity = ?, "
            "updated_at = datetime('now') WHERE id = 1",
            (row["mood"], row["sensitivity"]),
        )
        conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Error Recovery
# ---------------------------------------------------------------------------

def get_failed_analyses() -> list[dict]:
    """Images that failed analysis (is_analyzed=0 with an error recorded)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM images WHERE is_active = 1 AND is_analyzed = 0 "
        "AND analysis_error != '' ORDER BY uploaded_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_image_error(image_id: str, error: str, retry_count: int) -> None:
    """Records an analysis failure on an image."""
    conn = get_connection()
    conn.execute(
        "UPDATE images SET analysis_error = ?, retry_count = ? WHERE id = ?",
        (error, retry_count, image_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Image Scheduling
# ---------------------------------------------------------------------------

def get_scheduled_images(current_date: str = "", current_period: str = "") -> list[dict]:
    """
    Returns analyzed, active images that are within their schedule window.
    Falls back to get_analyzed_images() behaviour when no scheduling columns exist.
    """
    conn = get_connection()
    conditions = ["i.is_active = 1", "i.is_analyzed = 1"]
    params: list = []

    if current_date:
        conditions.append("(i.schedule_start IS NULL OR i.schedule_start <= ?)")
        conditions.append("(i.schedule_end IS NULL OR i.schedule_end >= ?)")
        params.extend([current_date, current_date])

    if current_period:
        conditions.append(
            "(i.time_window = 'any' OR i.time_window LIKE ?)"
        )
        params.append(f"%{current_period}%")

    where = " WHERE " + " AND ".join(conditions)
    sql = f"SELECT i.* FROM images i{where} ORDER BY i.last_displayed ASC"

    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        # Fallback if scheduling columns don't exist yet
        rows = conn.execute(
            "SELECT * FROM images WHERE is_active = 1 AND is_analyzed = 1 "
            "ORDER BY last_displayed ASC NULLS FIRST"
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def update_image_schedule(
    image_id: str, schedule_start: str, schedule_end: str, time_window: str
) -> None:
    """Sets scheduling constraints on an image."""
    conn = get_connection()
    conn.execute(
        "UPDATE images SET schedule_start = ?, schedule_end = ?, time_window = ? WHERE id = ?",
        (schedule_start or None, schedule_end or None, time_window, image_id),
    )
    conn.commit()
    conn.close()
