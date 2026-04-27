"""
Chronos — Scenario Test Runner
================================

Runs predefined contextual scenarios against the live Decision Engine
and prints a structured evaluation report.

For CIS4517 scenario-based testing — assesses:
  • Consistency and coherence of image selection
  • Responsiveness to contextual changes
  • Responsiveness to user control (mood preference, sensitivity)

Every call to select_best_image() writes to context_logs automatically,
so all scenario runs are also visible in the main app → Recent History.

Usage:
    python tests/scenario_runner.py
    python tests/scenario_runner.py --quiet   (scores only, no breakdown)
"""

import argparse
import sys
from pathlib import Path

# Allow imports from the project root regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logic.engine  import select_best_image
from database.queries import (
    get_all_images, get_preferences, get_interaction_counts, update_preferences,
    get_user_by_username
)
from services.manager   import ChronosManager


# ---------------------------------------------------------------------------
# Scenario Definitions
# ---------------------------------------------------------------------------

TIME_SCENARIOS = [
    {"label": "Dawn       (05:00)", "time_period": "dawn",      "detected_mood": "calm",        "hour": 5,  "minute": 0},
    {"label": "Morning    (09:00)", "time_period": "morning",   "detected_mood": "energetic",   "hour": 9,  "minute": 0},
    {"label": "Afternoon  (14:00)", "time_period": "afternoon", "detected_mood": "joyful",      "hour": 14, "minute": 0},
    {"label": "Evening    (18:30)", "time_period": "evening",   "detected_mood": "calm",        "hour": 18, "minute": 30},
    {"label": "Night      (22:00)", "time_period": "night",     "detected_mood": "mysterious",  "hour": 22, "minute": 0},
]

MOOD_OVERRIDES  = ["calm", "energetic", "joyful", "melancholic", "mysterious", "neutral"]
SENSITIVITY_LEVELS = ["low", "medium", "high"]

SEP  = "-" * 78
SEP2 = "=" * 78

class Logger:
    def __init__(self, filepath=None):
        self.file = open(filepath, 'w', encoding='utf-8') if filepath else None
    
    def log(self, msg=""):
        print(msg)
        if self.file:
            self.file.write(str(msg) + "\n")
            
    def close(self):
        if self.file:
            self.file.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result_row(result, label: str) -> str:
    if result is None:
        return f"  {label:<30}  {'No images available':<28}  —"
    title = (result.image.get("title") or "Untitled")[:27]
    bd    = result.breakdown
    breakdown = (
        f"T:{bd.get('time',0):.2f}  "
        f"M:{bd.get('mood',0):.2f}  "
        f"P:{bd.get('preference',0):.2f}  "
        f"I:{bd.get('interaction',0):+.2f}"
    )
    return f"  {label:<30}  {title:<28}  {result.total_score:.2f}  {breakdown}"


def _header(cols: list[str]) -> str:
    return f"  {'Scenario':<30}  {'Selected Image':<28}  {'Score':5}  {cols[0]}"


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

def run_all(quiet: bool = False, output_file: str = None, user_id: str = "") -> None:
    l = Logger(output_file)
    images = get_all_images(active_only=True, user_id=user_id)
    original = get_preferences(user_id=user_id)

    l.log()
    l.log(SEP2)
    l.log("  CHRONOS — SCENARIO TEST RUNNER")
    l.log(f"  {len(images)} image(s) in library (User: {user_id or 'Global'})")
    l.log(SEP2)

    if not images:
        l.log("  [!]  No images found. Add and analyse images via the main app first.")
        l.log(SEP2)
        l.close()
        return

    # Show interaction counts for context
    if not quiet:
        l.log()
        l.log("  Image Interaction Summary (likes / skips recorded so far):")
        l.log(f"  {'Title':<32}  {'Mood':<12}  {'Time':<12}  {'Likes':>5}  {'Skips':>5}")
        l.log("  " + SEP[2:])
        for img in images:
            counts = get_interaction_counts(img["id"])
            title  = (img.get("title") or "Untitled")[:31]
            mood   = img.get("primary_mood", "—")[:11]
            time   = img.get("optimal_time", "—")[:11]
            l.log(f"  {title:<32}  {mood:<12}  {time:<12}  {counts['like']:>5}  {counts['skip']:>5}")

    # ── TEST 1: Time Period Scenarios ──────────────────────────────────────
    l.log()
    l.log(SEP)
    l.log("  TEST 1 — Time Period Coverage  (default preferences)")
    l.log(SEP)
    l.log(_header(["Breakdown (T=time, M=mood, P=pref, I=interaction)"]))
    l.log("  " + SEP[2:])

    update_preferences(sensitivity="medium", user_id=user_id)
    for s in TIME_SCENARIOS:
        ctx    = {k: v for k, v in s.items() if k != "label"}
        result = select_best_image(ctx, user_id=user_id)
        l.log(_result_row(result, s["label"]))

    # ── TEST 2: Sensitivity Levels ─────────────────────────────────────────
    l.log()
    l.log(SEP)
    l.log("  TEST 2 — Sensitivity Levels  (afternoon/joyful context)")
    l.log(SEP)
    l.log(_header(["Breakdown"]))
    l.log("  " + SEP[2:])

    afternoon = {"time_period": "afternoon", "detected_mood": "joyful", "hour": 14, "minute": 0}
    for sens in SENSITIVITY_LEVELS:
        update_preferences(sensitivity=sens, user_id=user_id)
        result = select_best_image(afternoon, user_id=user_id)
        l.log(_result_row(result, f"Sensitivity = {sens}"))

    # ── TEST 3: Preferred Mood Override ────────────────────────────────────
    l.log()
    l.log(SEP)
    l.log("  TEST 3 — Preferred Mood Override  (evening/calm context)")
    l.log(SEP)
    l.log(_header(["Breakdown"]))
    l.log("  " + SEP[2:])

    evening = {"time_period": "evening", "detected_mood": "calm", "hour": 19, "minute": 0}
    update_preferences(sensitivity="medium", user_id=user_id)
    for mood in MOOD_OVERRIDES:
        update_preferences(preferred_mood=mood, user_id=user_id)
        result = select_best_image(evening, user_id=user_id)
        l.log(_result_row(result, f"Preferred mood = {mood}"))

    # ── TEST 4: Interaction Signal ─────────────────────────────────────────
    if not quiet and len(images) > 1:
        l.log()
        l.log(SEP)
        l.log("  TEST 4 — Interaction Signal  (does like/skip change selection?)")
        l.log(SEP)
        l.log("  Running afternoon context before and after 3 likes on top image...")
        l.log()

        update_preferences(sensitivity="medium", preferred_mood=original.get("preferred_mood", "calm"), user_id=user_id)
        result_before = select_best_image(afternoon, user_id=user_id)
        if result_before:
            top_id = result_before.image["id"]
            top_title = (result_before.image.get("title") or "Untitled")[:27]
            l.log(f"  Before:  {top_title:<28}  score={result_before.total_score:.3f}")

            # Temporarily add 3 likes to trigger the interaction delta
            from database.queries import save_interaction
            for _ in range(3):
                save_interaction(top_id, "like", user_id=user_id)

            result_after = select_best_image(afternoon, user_id=user_id)
            if result_after:
                after_title = (result_after.image.get("title") or "Untitled")[:27]
                delta = result_after.total_score - result_before.total_score
                l.log(f"  After 3 likes: {after_title:<24}  score={result_after.total_score:.3f}  (d{delta:+.3f})")

            # Clean up test likes
            conn_cleanup()

    # ── TEST 5: Profile Safety (Kids Mode) ──────────────────────────────────
    l.log()
    l.log(SEP)
    l.log("  TEST 5 — Profile Safety Filter (Kids Mode vs Standard)")
    l.log(SEP)
    l.log("  Verifying that Kids profile applies stricter mood filtering...")
    l.log()
    
    # Reset to baseline
    update_preferences(sensitivity="medium", preferred_mood="calm", user_id=user_id)
    
    # Pick a "mysterious" or "melancholic" context which might be filtered for Kids
    test_ctx = {"time_period": "night", "detected_mood": "mysterious", "hour": 23, "minute": 30}
    
    res_std = select_best_image(test_ctx, user_id=user_id, profile_type="Standard")
    res_kids = select_best_image(test_ctx, user_id=user_id, profile_type="Kids")
    
    title_std = (res_std.image.get("title") or "None") if res_std else "None"
    title_kids = (res_kids.image.get("title") or "None") if res_kids else "None"
    
    l.log(f"  Standard Profile: {title_std:<28}")
    l.log(f"  Kids Profile:     {title_kids:<28}")
    
    if res_kids and res_kids.filter_notes:
        for note in res_kids.filter_notes:
            l.log(f"    [Filter Note]: {note}")

    # ── Restore preferences ────────────────────────────────────────────────
    update_preferences(
        preferred_mood=original.get("preferred_mood", "calm"),
        sensitivity=original.get("sensitivity", "medium"),
        user_id=user_id
    )

    l.log()
    l.log(SEP2)
    l.log("  All scenarios saved to context_logs.")
    l.log("  View results: main app -> sidebar -> Recent History")
    l.log(SEP2)
    l.log()
    l.close()


def conn_cleanup() -> None:
    """Remove the 3 test likes added during Test 4 to keep data clean."""
    try:
        from database.schema import get_connection
        conn = get_connection()
        conn.execute(
            "DELETE FROM image_interactions WHERE id IN "
            "(SELECT id FROM image_interactions WHERE interaction='like' "
            "ORDER BY timestamp DESC LIMIT 3)"
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Non-critical cleanup


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from database import init_database
    init_database()
    
    parser = argparse.ArgumentParser(description="Chronos scenario test runner")
    parser.add_argument("--quiet", action="store_true", help="Suppress interaction summary and Test 4")
    parser.add_argument("--output", type=str, help="Save report to this file")
    parser.add_argument("--username", type=str, help="Run as specific user")
    args = parser.parse_args()
    
    uid = ""
    if args.username:
        user = get_user_by_username(args.username)
        if user:
            uid = user["id"]
        else:
            print(f"Error: User '{args.username}' not found.")
            sys.exit(1)
            
    run_all(quiet=args.quiet, output_file=args.output, user_id=uid)
