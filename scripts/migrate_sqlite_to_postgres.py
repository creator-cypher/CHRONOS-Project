#!/usr/bin/env python3
"""
CHRONOS SQLite to PostgreSQL Migration Script
==============================================

Migrates all data from SQLite database to PostgreSQL while preserving
all data integrity and relationships.

Usage:
    python migrate_sqlite_to_postgres.py \
        --sqlite_path ./Chronos/chronos.db \
        --postgres_url postgresql://user:pass@localhost:5432/db
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import argparse
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid as uuid_module

# Import PostgreSQL models
sys.path.insert(0, str(Path(__file__).parent.parent / "Chronos"))
from database.postgres_schema import (
    Base, Image, ImageTag, UserPreference, ContextLog,
    DisplayConfig, ImageInteraction, init_database
)


class SQLiteToPgMigrator:
    """Handles migration from SQLite to PostgreSQL"""

    def __init__(self, sqlite_path: str, postgres_url: str):
        self.sqlite_path = Path(sqlite_path)
        self.postgres_url = postgres_url

        # SQLite connection
        self.sqlite_conn = sqlite3.connect(str(self.sqlite_path))
        self.sqlite_conn.row_factory = sqlite3.Row

        # PostgreSQL connection
        self.pg_engine = create_engine(postgres_url)
        self.pg_session = sessionmaker(bind=self.pg_engine)()

        self.stats = {
            'images': 0,
            'tags': 0,
            'preferences': 0,
            'logs': 0,
            'interactions': 0,
            'config': 0,
            'errors': 0
        }

    def migrate_images(self) -> bool:
        """Migrate images table"""
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT * FROM images")
            rows = cursor.fetchall()

            for row in rows:
                image = Image(
                    id=row['id'] or str(uuid_module.uuid4()),
                    title=row['title'],
                    image_path=row['image_path'],
                    image_url=row['image_url'],
                    ai_description=row['ai_description'],
                    dominant_colors=json.loads(row['dominant_colors']) if row['dominant_colors'] else [],
                    primary_mood=row['primary_mood'],
                    optimal_time=row['optimal_time'],
                    base_score=float(row['base_score']),
                    display_count=int(row['display_count']),
                    last_displayed=row['last_displayed'],
                    is_analyzed=bool(row['is_analyzed']),
                    is_active=bool(row['is_active']),
                    uploaded_at=datetime.fromisoformat(row['uploaded_at'].replace('Z', '+00:00'))
                        if row['uploaded_at'] else datetime.now()
                )
                self.pg_session.add(image)
                self.stats['images'] += 1

            self.pg_session.commit()
            print(f"✓ Migrated {self.stats['images']} images")
            return True
        except Exception as e:
            print(f"✗ Error migrating images: {e}")
            self.stats['errors'] += 1
            self.pg_session.rollback()
            return False

    def migrate_image_tags(self) -> bool:
        """Migrate image_tags table"""
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT * FROM image_tags")
            rows = cursor.fetchall()

            for row in rows:
                tag = ImageTag(
                    image_id=row['image_id'],
                    name=row['name'],
                    category=row['category'],
                    confidence=float(row['confidence'])
                )
                self.pg_session.add(tag)
                self.stats['tags'] += 1

            self.pg_session.commit()
            print(f"✓ Migrated {self.stats['tags']} image tags")
            return True
        except Exception as e:
            print(f"✗ Error migrating tags: {e}")
            self.stats['errors'] += 1
            self.pg_session.rollback()
            return False

    def migrate_user_preferences(self) -> bool:
        """Migrate user_preferences table"""
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT * FROM user_preferences")
            rows = cursor.fetchall()

            for row in rows:
                pref = UserPreference(
                    id=row['id'],
                    preferred_mood=row['preferred_mood'],
                    sensitivity=row['sensitivity'],
                    time_mood_map=json.loads(row['time_mood_map']) if row['time_mood_map'] else {},
                    override_active=bool(row['override_active']),
                    override_image_id=row['override_image_id'],
                    recency_weight=float(row['recency_weight']),
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                        if row['updated_at'] else datetime.now()
                )
                self.pg_session.add(pref)
                self.stats['preferences'] += 1

            self.pg_session.commit()
            print(f"✓ Migrated {self.stats['preferences']} user preferences")
            return True
        except Exception as e:
            print(f"✗ Error migrating preferences: {e}")
            self.stats['errors'] += 1
            self.pg_session.rollback()
            return False

    def migrate_context_logs(self) -> bool:
        """Migrate context_logs table"""
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT * FROM context_logs")
            rows = cursor.fetchall()

            for row in rows:
                log = ContextLog(
                    timestamp=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                        if row['timestamp'] else datetime.now(),
                    time_period=row['time_period'],
                    detected_mood=row['detected_mood'],
                    selected_image_id=row['selected_image_id'],
                    selection_score=float(row['selection_score']),
                    score_breakdown=json.loads(row['score_breakdown']) if row['score_breakdown'] else {},
                    matched_tags=json.loads(row['matched_tags']) if row['matched_tags'] else [],
                    reasoning_text=row['reasoning_text'],
                    was_override=bool(row['was_override'])
                )
                self.pg_session.add(log)
                self.stats['logs'] += 1

            self.pg_session.commit()
            print(f"✓ Migrated {self.stats['logs']} context logs")
            return True
        except Exception as e:
            print(f"✗ Error migrating logs: {e}")
            self.stats['errors'] += 1
            self.pg_session.rollback()
            return False

    def migrate_display_config(self) -> bool:
        """Migrate display_config table"""
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT * FROM display_config")
            rows = cursor.fetchall()

            for row in rows:
                config = DisplayConfig(
                    id=row['id'],
                    poll_interval_seconds=int(row['poll_interval_seconds']),
                    transition_duration_ms=int(row['transition_duration_ms']),
                    show_reasoning_overlay=bool(row['show_reasoning_overlay']),
                    overlay_auto_hide_seconds=int(row['overlay_auto_hide_seconds']),
                    night_brightness=float(row['night_brightness']),
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                        if row['updated_at'] else datetime.now()
                )
                self.pg_session.add(config)
                self.stats['config'] += 1

            self.pg_session.commit()
            print(f"✓ Migrated {self.stats['config']} display configs")
            return True
        except Exception as e:
            print(f"✗ Error migrating config: {e}")
            self.stats['errors'] += 1
            self.pg_session.rollback()
            return False

    def migrate_interactions(self) -> bool:
        """Migrate image_interactions table"""
        try:
            cursor = self.sqlite_conn.cursor()
            cursor.execute("SELECT * FROM image_interactions")
            rows = cursor.fetchall()

            for row in rows:
                interaction = ImageInteraction(
                    image_id=row['image_id'],
                    interaction=row['interaction'],
                    timestamp=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                        if row['timestamp'] else datetime.now()
                )
                self.pg_session.add(interaction)
                self.stats['interactions'] += 1

            self.pg_session.commit()
            print(f"✓ Migrated {self.stats['interactions']} interactions")
            return True
        except Exception as e:
            print(f"✗ Error migrating interactions: {e}")
            self.stats['errors'] += 1
            self.pg_session.rollback()
            return False

    def run(self) -> bool:
        """Execute full migration"""
        print("\n" + "="*60)
        print("CHRONOS SQLite → PostgreSQL Migration")
        print("="*60)

        # Verify SQLite file exists
        if not self.sqlite_path.exists():
            print(f"✗ SQLite file not found: {self.sqlite_path}")
            return False

        print(f"📂 SQLite: {self.sqlite_path}")
        print(f"🐘 PostgreSQL: {self.postgres_url.split('@')[1] if '@' in self.postgres_url else 'localhost'}")

        # Initialize PostgreSQL schema
        print("\n[1/2] Initializing PostgreSQL schema...")
        try:
            init_database()
            print("✓ Database schema created")
        except Exception as e:
            print(f"✗ Failed to initialize schema: {e}")
            return False

        # Migrate data
        print("\n[2/2] Migrating data...")
        success = all([
            self.migrate_images(),
            self.migrate_image_tags(),
            self.migrate_user_preferences(),
            self.migrate_context_logs(),
            self.migrate_display_config(),
            self.migrate_interactions(),
        ])

        # Print summary
        print("\n" + "="*60)
        print("Migration Summary")
        print("="*60)
        for key, value in self.stats.items():
            status = "✓" if value > 0 or key == 'errors' else "⚠"
            print(f"{status} {key.ljust(20)}: {value}")

        print("="*60)

        # Cleanup
        self.sqlite_conn.close()
        self.pg_session.close()

        if self.stats['errors'] > 0:
            print(f"\n⚠ Migration completed with {self.stats['errors']} error(s)")
            return False
        else:
            print("\n✅ Migration completed successfully!")
            return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate CHRONOS database from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite_path",
        required=True,
        help="Path to SQLite database file"
    )
    parser.add_argument(
        "--postgres_url",
        required=True,
        help="PostgreSQL connection URL"
    )

    args = parser.parse_args()

    migrator = SQLiteToPgMigrator(args.sqlite_path, args.postgres_url)
    success = migrator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
