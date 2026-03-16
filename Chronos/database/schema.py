"""
Chronos — SQLite Schema & Initialisation
==========================================

Without Django's ORM, we manage the database directly with Python's
built-in `sqlite3` module. This keeps the dependency footprint minimal
and makes the schema immediately transparent.

Table design mirrors the Django models from the CONTESS architecture:
  images          → api.models.Image
  image_tags      → api.models.ImageTag
  user_preferences → api.models.UserPreference
  context_logs    → api.models.ContextLog
  display_config  → core.models.DisplayConfig

The `get_connection()` helper sets `row_factory = sqlite3.Row` so every
query returns dict-like rows, accessed by column name rather than index.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "chronos.db"


# ---------------------------------------------------------------------------
# Table Definitions
# ---------------------------------------------------------------------------

_CREATE_IMAGES = """
CREATE TABLE IF NOT EXISTS images (
    id            TEXT    PRIMARY KEY,
    title         TEXT    NOT NULL DEFAULT '',
    image_path    TEXT    NOT NULL DEFAULT '',
    image_url     TEXT    NOT NULL DEFAULT '',
    ai_description TEXT   NOT NULL DEFAULT '',
    dominant_colors TEXT  NOT NULL DEFAULT '[]',
    primary_mood  TEXT    NOT NULL DEFAULT 'neutral',
    optimal_time  TEXT    NOT NULL DEFAULT 'any',
    base_score    REAL    NOT NULL DEFAULT 0.5,
    display_count INTEGER NOT NULL DEFAULT 0,
    last_displayed TEXT,
    is_analyzed   INTEGER NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 1,
    uploaded_at   TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_TAGS = """
CREATE TABLE IF NOT EXISTS image_tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id   TEXT    NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    category   TEXT    NOT NULL DEFAULT 'subject',
    confidence REAL    NOT NULL DEFAULT 1.0,
    UNIQUE(image_id, name)
)
"""

_CREATE_PREFERENCES = """
CREATE TABLE IF NOT EXISTS user_preferences (
    id               INTEGER PRIMARY KEY,
    preferred_mood   TEXT    NOT NULL DEFAULT 'calm',
    sensitivity      TEXT    NOT NULL DEFAULT 'medium',
    time_mood_map    TEXT    NOT NULL DEFAULT '{}',
    override_active  INTEGER NOT NULL DEFAULT 0,
    override_image_id TEXT,
    recency_weight   REAL    NOT NULL DEFAULT 0.2,
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS context_logs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT    NOT NULL DEFAULT (datetime('now')),
    time_period       TEXT    NOT NULL DEFAULT '',
    detected_mood     TEXT    NOT NULL DEFAULT '',
    selected_image_id TEXT    REFERENCES images(id) ON DELETE SET NULL,
    selection_score   REAL    NOT NULL DEFAULT 0.0,
    score_breakdown   TEXT    NOT NULL DEFAULT '{}',
    matched_tags      TEXT    NOT NULL DEFAULT '[]',
    reasoning_text    TEXT    NOT NULL DEFAULT '',
    was_override      INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_DISPLAY_CONFIG = """
CREATE TABLE IF NOT EXISTS display_config (
    id                       INTEGER PRIMARY KEY,
    poll_interval_seconds    INTEGER NOT NULL DEFAULT 300,
    transition_duration_ms   INTEGER NOT NULL DEFAULT 1500,
    show_reasoning_overlay   INTEGER NOT NULL DEFAULT 1,
    overlay_auto_hide_seconds INTEGER NOT NULL DEFAULT 8,
    night_brightness         REAL    NOT NULL DEFAULT 0.7,
    updated_at               TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_INTERACTIONS = """
CREATE TABLE IF NOT EXISTS image_interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id    TEXT    NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    interaction TEXT    NOT NULL CHECK(interaction IN ('like', 'skip')),
    timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_PRESETS = """
CREATE TABLE IF NOT EXISTS presets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    mood        TEXT    NOT NULL DEFAULT 'calm',
    sensitivity TEXT    NOT NULL DEFAULT 'medium',
    is_default  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

# Indexes for the Decision Engine's query patterns
_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mood_time       ON images(primary_mood, optimal_time)",
    "CREATE INDEX IF NOT EXISTS idx_active           ON images(is_active, is_analyzed)",
    "CREATE INDEX IF NOT EXISTS idx_images_title     ON images(title)",
    "CREATE INDEX IF NOT EXISTS idx_log_ts           ON context_logs(timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS idx_log_image_id     ON context_logs(selected_image_id)",
    "CREATE INDEX IF NOT EXISTS idx_interactions     ON image_interactions(image_id, interaction)",
    "CREATE INDEX IF NOT EXISTS idx_interactions_ts  ON image_interactions(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_tags_image_id    ON image_tags(image_id)",
    "CREATE INDEX IF NOT EXISTS idx_tags_name        ON image_tags(name)",
    "CREATE INDEX IF NOT EXISTS idx_tags_category    ON image_tags(category)",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Opens a connection to the Chronos SQLite database.
    Sets `row_factory = sqlite3.Row` for dict-style column access.
    Enables WAL mode for better concurrent read performance.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database() -> None:
    """
    Creates all tables and indexes if they do not exist.
    Also seeds the singleton rows for user_preferences and display_config.
    Safe to call on every application startup (idempotent).
    """
    conn = get_connection()
    cur  = conn.cursor()

    for ddl in [
        _CREATE_IMAGES,
        _CREATE_TAGS,
        _CREATE_PREFERENCES,
        _CREATE_LOGS,
        _CREATE_DISPLAY_CONFIG,
        _CREATE_INTERACTIONS,
        _CREATE_PRESETS,
        *_CREATE_INDEXES,
    ]:
        cur.execute(ddl)

    # ── Migrations: add columns for new features (idempotent) ────────────
    _migrations = [
        # Error recovery (Enhancement 7)
        "ALTER TABLE images ADD COLUMN analysis_error TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE images ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0",
        # Image scheduling (Enhancement 9)
        "ALTER TABLE images ADD COLUMN schedule_start TEXT DEFAULT NULL",
        "ALTER TABLE images ADD COLUMN schedule_end TEXT DEFAULT NULL",
        "ALTER TABLE images ADD COLUMN time_window TEXT NOT NULL DEFAULT 'any'",
        # Vision API prompt config (Enhancement 10)
        "ALTER TABLE display_config ADD COLUMN analysis_depth TEXT NOT NULL DEFAULT 'standard'",
        "ALTER TABLE display_config ADD COLUMN analysis_focus TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE display_config ADD COLUMN custom_prompt TEXT NOT NULL DEFAULT ''",
    ]
    for sql in _migrations:
        try:
            cur.execute(sql)
        except Exception:
            pass  # Column already exists — safe to ignore

    # Seed singleton rows — INSERT OR IGNORE ensures we never overwrite data
    cur.execute("INSERT OR IGNORE INTO user_preferences (id) VALUES (1)")
    cur.execute("INSERT OR IGNORE INTO display_config    (id) VALUES (1)")

    # Seed default presets
    for name, mood, sensitivity in [
        ("Morning Energy", "energetic", "high"),
        ("Evening Calm", "calm", "medium"),
        ("Night Mystery", "mysterious", "high"),
    ]:
        cur.execute(
            "INSERT OR IGNORE INTO presets (name, mood, sensitivity, is_default) "
            "VALUES (?, ?, ?, 1)",
            (name, mood, sensitivity),
        )

    conn.commit()
    conn.close()
