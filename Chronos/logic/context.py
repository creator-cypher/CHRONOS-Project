"""
Chronos — Context Management
==============================

Determines the current environmental context from the system clock.
Adapted from core/context.py (Django version) — all Django imports removed.

Returns a plain dict consumed directly by the Decision Engine.
"""

from datetime import datetime
from typing import Optional


TIME_PERIODS: list[tuple[int, int, str, str]] = [
    (  5,  8,  "dawn",      "calm"      ),
    (  8, 12,  "morning",   "energetic" ),
    ( 12, 17,  "afternoon", "joyful"    ),
    ( 17, 21,  "evening",   "calm"      ),
    ( 21, 24,  "night",     "mysterious"),
    (  0,  5,  "night",     "mysterious"),
]

SEASONS: dict[int, str] = {
    12: "winter", 1: "winter",  2: "winter",
    3:  "spring", 4: "spring",  5: "spring",
    6:  "summer", 7: "summer",  8: "summer",
    9:  "autumn", 10: "autumn", 11: "autumn",
}

TIME_PERIOD_ICONS: dict[str, str] = {
    "dawn": "🌅", "morning": "☀️",
    "afternoon": "🌤", "evening": "🌆", "night": "🌙",
}


def get_current_context(overrides: Optional[dict] = None) -> dict:
    """
    Returns the full environmental context for the current moment.

    Validates all mood and period values to prevent silent scoring degradation.
    If overrides contain invalid values, they are sanitized to safe defaults.
    """
    now    = datetime.now()
    hour   = now.hour
    period, mood = _classify_time(hour)

    ctx = {
        "time_period":   period,
        "hour":          hour,
        "minute":        now.minute,
        "detected_mood": mood,
        "day_of_week":   now.strftime("%A"),
        "is_weekend":    now.weekday() >= 5,
        "season":        SEASONS.get(now.month, "spring"),
        "period_icon":   TIME_PERIOD_ICONS.get(period, "🕐"),
        "timestamp":     now.isoformat(),
    }

    if overrides:
        ctx.update(overrides)

    # Validate mood and period to prevent downstream scoring dead ends
    valid_moods = {"calm", "energetic", "melancholic", "joyful", "mysterious", "neutral"}
    valid_periods = {"dawn", "morning", "afternoon", "evening", "night", "any"}

    if ctx.get("detected_mood") not in valid_moods:
        ctx["detected_mood"] = "neutral"
    if ctx.get("time_period") not in valid_periods:
        ctx["time_period"] = "any"

    return ctx


def get_time_period(hour: Optional[int] = None) -> str:
    if hour is None:
        hour = datetime.now().hour
    period, _ = _classify_time(hour)
    return period


def get_period_mood(time_period: str) -> str:
    defaults = {
        "dawn": "calm", "morning": "energetic",
        "afternoon": "joyful", "evening": "calm", "night": "mysterious",
    }
    return defaults.get(time_period, "neutral")


def _classify_time(hour: int) -> tuple[str, str]:
    for start, end, period, mood in TIME_PERIODS:
        if start <= hour < end:
            return period, mood
    return "night", "mysterious"
