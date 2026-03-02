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
)


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

SEP  = "─" * 78
SEP2 = "═" * 78


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

def run_all(quiet: bool = False) -> None:
    images = get_all_images(active_only=True)
    original = get_preferences()

    print()
    print(SEP2)
    print("  CHRONOS — SCENARIO TEST RUNNER")
    print(f"  {len(images)} image(s) in library")
    print(SEP2)

    if not images:
        print("  ⚠  No images found. Add and analyse images via the main app first.")
        print(SEP2)
        return

    # Show interaction counts for context
    if not quiet:
        print()
        print("  Image Interaction Summary (likes / skips recorded so far):")
        print(f"  {'Title':<32}  {'Mood':<12}  {'Time':<12}  {'Likes':>5}  {'Skips':>5}")
        print("  " + SEP[2:])
        for img in images:
            counts = get_interaction_counts(img["id"])
            title  = (img.get("title") or "Untitled")[:31]
            mood   = img.get("primary_mood", "—")[:11]
            time   = img.get("optimal_time", "—")[:11]
            print(f"  {title:<32}  {mood:<12}  {time:<12}  {counts['like']:>5}  {counts['skip']:>5}")

    # ── TEST 1: Time Period Scenarios ──────────────────────────────────────
    print()
    print(SEP)
    print("  TEST 1 — Time Period Coverage  (default preferences)")
    print(SEP)
    print(_header(["Breakdown (T=time, M=mood, P=pref, I=interaction)"]))
    print("  " + SEP[2:])

    update_preferences(sensitivity="medium")
    for s in TIME_SCENARIOS:
        ctx    = {k: v for k, v in s.items() if k != "label"}
        result = select_best_image(ctx)
        print(_result_row(result, s["label"]))

    # ── TEST 2: Sensitivity Levels ─────────────────────────────────────────
    print()
    print(SEP)
    print("  TEST 2 — Sensitivity Levels  (afternoon/joyful context)")
    print(SEP)
    print(_header(["Breakdown"]))
    print("  " + SEP[2:])

    afternoon = {"time_period": "afternoon", "detected_mood": "joyful", "hour": 14, "minute": 0}
    for sens in SENSITIVITY_LEVELS:
        update_preferences(sensitivity=sens)
        result = select_best_image(afternoon)
        print(_result_row(result, f"Sensitivity = {sens}"))

    # ── TEST 3: Preferred Mood Override ────────────────────────────────────
    print()
    print(SEP)
    print("  TEST 3 — Preferred Mood Override  (evening/calm context)")
    print(SEP)
    print(_header(["Breakdown"]))
    print("  " + SEP[2:])

    evening = {"time_period": "evening", "detected_mood": "calm", "hour": 19, "minute": 0}
    update_preferences(sensitivity="medium")
    for mood in MOOD_OVERRIDES:
        update_preferences(preferred_mood=mood)
        result = select_best_image(evening)
        print(_result_row(result, f"Preferred mood = {mood}"))

    # ── TEST 4: Interaction Signal ─────────────────────────────────────────
    if not quiet and len(images) > 1:
        print()
        print(SEP)
        print("  TEST 4 — Interaction Signal  (does like/skip change selection?)")
        print(SEP)
        print("  Running afternoon context before and after 3 likes on top image...")
        print()

        update_preferences(sensitivity="medium", preferred_mood=original.get("preferred_mood", "calm"))
        result_before = select_best_image(afternoon)
        if result_before:
            top_id = result_before.image["id"]
            top_title = (result_before.image.get("title") or "Untitled")[:27]
            print(f"  Before:  {top_title:<28}  score={result_before.total_score:.3f}")

            # Temporarily add 3 likes to trigger the interaction delta
            from database.queries import save_interaction
            for _ in range(3):
                save_interaction(top_id, "like")

            result_after = select_best_image(afternoon)
            if result_after:
                after_title = (result_after.image.get("title") or "Untitled")[:27]
                delta = result_after.total_score - result_before.total_score
                print(f"  After 3 likes: {after_title:<24}  score={result_after.total_score:.3f}  (Δ{delta:+.3f})")

            # Clean up test likes
            conn_cleanup()

    # ── Restore preferences ────────────────────────────────────────────────
    update_preferences(
        preferred_mood=original.get("preferred_mood", "calm"),
        sensitivity=original.get("sensitivity", "medium"),
    )

    print()
    print(SEP2)
    print("  All scenarios saved to context_logs.")
    print("  View results: main app → sidebar → 🕐 Recent History")
    print(SEP2)
    print()


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
    parser = argparse.ArgumentParser(description="Chronos scenario test runner")
    parser.add_argument("--quiet", action="store_true", help="Suppress interaction summary and Test 4")
    args = parser.parse_args()
    run_all(quiet=args.quiet)
