"""
Chronos — Weighted Decision Engine (Streamlit edition)
=======================================================

Identical algorithm to api/logic.py (Django version) but operates on
plain Python dicts returned by database/queries.py instead of ORM objects.

Score = w_time × time_score  +  w_mood × mood_score
      + w_pref × pref_score  +  w_qual × quality_score
      - w_rec  × recency_penalty
      + interaction_delta   (capped ±0.15 from user likes/skips)

Weights shift based on UserPreference.sensitivity (low / medium / high).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from database.queries import (
    get_analyzed_images,
    get_scheduled_images,
    get_interaction_counts,
    get_preferences,
    get_recently_shown_ids,
    get_tags_for_image,
    save_context_log,
    update_image_display_stats,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weight Profiles
# ---------------------------------------------------------------------------

WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "low":    {"time": 0.20, "mood": 0.15, "preference": 0.40, "quality": 0.15, "recency": 0.10},
    "medium": {"time": 0.35, "mood": 0.25, "preference": 0.20, "quality": 0.10, "recency": 0.10},
    "high":   {"time": 0.40, "mood": 0.30, "preference": 0.10, "quality": 0.10, "recency": 0.10},
}

MOOD_COMPAT: dict[str, dict[str, float]] = {
    "calm":        {"calm": 1.0, "melancholic": 0.5, "neutral": 0.4},
    "energetic":   {"energetic": 1.0, "joyful": 0.6, "neutral": 0.3},
    "melancholic": {"melancholic": 1.0, "calm": 0.5, "mysterious": 0.4},
    "joyful":      {"joyful": 1.0, "energetic": 0.6, "neutral": 0.3},
    "mysterious":  {"mysterious": 1.0, "melancholic": 0.4, "calm": 0.3},
    "neutral":     {"neutral": 1.0, "calm": 0.4, "joyful": 0.4},
}

# Seasonality factor: colour temperature & visual warmth by season
# Warmer tones (oranges, reds) boost in winter; cooler tones (blues, greens) boost in summer
SEASONALITY_MOODS: dict[str, dict[str, float]] = {
    "winter":   {"calm": 1.1, "mysterious": 1.15, "melancholic": 1.05, "neutral": 1.0, "energetic": 0.9, "joyful": 0.95},
    "spring":   {"joyful": 1.15, "energetic": 1.10, "calm": 1.0, "neutral": 1.0, "melancholic": 0.85, "mysterious": 0.9},
    "summer":   {"energetic": 1.20, "joyful": 1.15, "calm": 0.95, "neutral": 1.0, "mysterious": 0.85, "melancholic": 0.8},
    "autumn":   {"mysterious": 1.15, "melancholic": 1.10, "calm": 1.05, "neutral": 1.0, "energetic": 0.95, "joyful": 0.9},
}

TIME_ADJACENT: dict[str, list[str]] = {
    "dawn":      ["dawn", "morning"],
    "morning":   ["morning", "dawn", "afternoon"],
    "afternoon": ["afternoon", "morning", "evening"],
    "evening":   ["evening", "afternoon", "night"],
    "night":     ["night", "evening"],
    "any":       ["dawn", "morning", "afternoon", "evening", "night", "any"],
}


# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------

@dataclass
class SelectionResult:
    image:           dict
    total_score:     float            = 0.0
    confidence_pct:  int              = 0  # 0-100% confidence in the selection
    breakdown:       dict             = field(default_factory=dict)
    matched_tags:    list[str]        = field(default_factory=list)
    reasoning_text:  str              = ""
    was_override:    bool             = False
    context:         dict             = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def select_best_image(context: dict) -> Optional[SelectionResult]:
    """
    Selects the optimal display image for the given context.

    Steps:
      1. Check for manual override → return immediately if active.
      2. Load all analysed + active candidate images.
      3. Score each candidate with the weighted algorithm.
      4. Pick the highest scorer, write an audit log, update stats.
    """
    prefs = get_preferences()

    # ── 1. Manual override ────────────────────────────────────────────────
    if prefs.get("override_active") and prefs.get("override_image_id"):
        from database.queries import get_image_by_id
        img = get_image_by_id(prefs["override_image_id"])
        if img:
            result = SelectionResult(
                image=img, total_score=1.0, confidence_pct=100,
                reasoning_text="Manual override active.",
                was_override=True, context=context,
            )
            _write_log(result, context)
            return result

    # ── 2. Candidate pool (with scheduling filter) ────────────────────────
    from datetime import datetime
    now = datetime.now()
    period = context.get("time_period", "")
    try:
        candidates = get_scheduled_images(
            current_date=now.strftime("%Y-%m-%d"),
            current_period=period,
        )
    except Exception:
        candidates = get_analyzed_images()
    if not candidates:
        logger.warning("No analysed images available.")
        return None

    # ── 3. Score ──────────────────────────────────────────────────────────
    weights         = WEIGHT_PROFILES.get(prefs.get("sensitivity", "medium"), WEIGHT_PROFILES["medium"])
    recently_shown  = get_recently_shown_ids(window_minutes=60)
    target_mood     = _resolve_mood(context, prefs)

    best: Optional[SelectionResult] = None
    best_score = -1.0

    for img in candidates:
        tags   = get_tags_for_image(img["id"])
        result = _score(img, tags, context, prefs, weights, recently_shown, target_mood)
        if result.total_score > best_score:
            best_score = result.total_score
            best = result

    if best is None:
        return None

    # ── 4. Persist & return ───────────────────────────────────────────────
    _write_log(best, context)
    update_image_display_stats(best.image["id"])
    return best


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score(
    img: dict,
    tags: list[dict],
    context: dict,
    prefs: dict,
    weights: dict,
    recently_shown: set,
    target_mood: str,
) -> SelectionResult:

    period      = context.get("time_period", "any")
    img_time    = img.get("optimal_time", "any")
    adjacent    = TIME_ADJACENT.get(period, [])

    # Time score
    if img_time == "any":
        t_score = 0.7
    elif img_time == period:
        t_score = 1.0
    elif img_time in adjacent:
        t_score = 0.5
    else:
        t_score = 0.1

    # Mood score — 60% from user preferred mood + 40% from time-detected mood.
    # Both the sidebar control and the time of day contribute independently.
    img_mood = img.get("primary_mood", "neutral")
    pref_map = MOOD_COMPAT.get(target_mood, {})
    det_map  = MOOD_COMPAT.get(context.get("detected_mood", "neutral"), {})
    m_score  = pref_map.get(img_mood, 0.0) * 0.60 + det_map.get(img_mood, 0.0) * 0.40

    # Seasonality boost: apply seasonal colour temperature preferences
    season = context.get("season", "spring")
    seasonal_boost = SEASONALITY_MOODS.get(season, {}).get(img_mood, 1.0)
    m_score = m_score * seasonal_boost

    # Preference score
    p_score = _preference_score(img, tags, target_mood)

    # Quality
    q_score = float(img.get("base_score", 0.5))

    # Recency penalty
    r_penalty = float(prefs.get("recency_weight", 0.2)) if img["id"] in recently_shown else 0.0

    total = max(0.0, min(1.0,
        weights["time"]       * t_score
        + weights["mood"]       * m_score
        + weights["preference"] * p_score
        + weights["quality"]    * q_score
        - weights["recency"]    * r_penalty
    ))

    # User feedback signal — each net like adds +0.05, each net skip −0.05, capped ±0.15
    counts  = get_interaction_counts(img["id"])
    net     = counts["like"] - counts["skip"]
    i_delta = max(-0.15, min(0.15, net * 0.05))
    total   = max(0.0, min(1.0, total + i_delta))

    matched = _find_matched_tags(tags, period, target_mood)
    reason  = _build_reason(context, target_mood, matched)

    # Calculate confidence percentage (0-100)
    # Base: total_score (0-1) → (0-60%)
    # Matched tags bonus: each matched tag adds 5%, capped at 30%
    # Override: manual selection gets 100%
    base_confidence = int(total * 60)
    tag_bonus = min(30, len(matched) * 5)
    confidence_pct = min(100, base_confidence + tag_bonus)

    return SelectionResult(
        image=img,
        total_score=round(total, 4),
        confidence_pct=confidence_pct,
        breakdown={"time": round(t_score, 3), "mood": round(m_score, 3),
                   "preference": round(p_score, 3), "quality": round(q_score, 3),
                   "recency": round(r_penalty, 3), "interaction": round(i_delta, 3)},
        matched_tags=matched,
        reasoning_text=reason,
        context=context,
    )


def _preference_score(img: dict, tags: list[dict], target_mood: str) -> float:
    """
    Scores how well an image's mood matches the target mood.

    Fixed: Now validates target_mood before lookup to prevent silent degradation.
    If target_mood is invalid, defaults to "neutral" mood_compat mapping.
    """
    # Validate target_mood to prevent empty mood_map → silent 0.0 score
    valid_moods = set(MOOD_COMPAT.keys())
    if target_mood not in valid_moods:
        target_mood = "neutral"

    mood_map   = MOOD_COMPAT.get(target_mood, {})
    mood_score = mood_map.get(img.get("primary_mood", "neutral"), 0.0)

    mood_tags = [t for t in tags if t["category"] == "mood" and t["confidence"] >= 0.6]
    tag_score = 0.0
    if mood_tags:
        hits      = sum(1 for t in mood_tags if t["name"] in mood_map)
        tag_score = min(1.0, hits / len(mood_tags))

    return mood_score * 0.7 + tag_score * 0.3


def _find_matched_tags(tags: list[dict], period: str, target_mood: str) -> list[str]:
    matched: list[str] = []
    for tag in tags:
        if tag.get("confidence", 0) < 0.5:
            continue
        name, cat = tag["name"].lower(), tag["category"]
        if cat == "time" and (period in name or name in period):
            matched.append(tag["name"])
        elif cat == "mood" and any(k in name for k in MOOD_COMPAT.get(target_mood, {})):
            matched.append(tag["name"])
        elif cat == "subject" and tag.get("confidence", 0) >= 0.8:
            matched.append(tag["name"])
    return matched[:6]


def _build_reason(context: dict, target_mood: str, matched: list) -> str:
    period   = context.get("time_period", "now").capitalize()
    tag_str  = "  ·  ".join(t.capitalize() for t in matched[:4])
    base     = f"Matched: {period} + {target_mood.capitalize()}"
    return f"{base}  |  {tag_str}" if tag_str else base


def _resolve_mood(context: dict, prefs: dict) -> str:
    """
    Resolves the target mood from user preferences and context.

    Priority:
      1. time_mood_map[period] — per-period user override (most specific)
      2. preferred_mood        — user's global preference (sidebar control)
      3. detected_mood         — auto-detected fallback from time of day

    preferred_mood now takes priority over detected_mood so the sidebar
    control has a genuine effect on image selection.
    """
    period   = context.get("time_period", "any")
    time_map = prefs.get("time_mood_map") or {}
    if period in time_map:
        return time_map[period]
    preferred = prefs.get("preferred_mood", "")
    if preferred:
        return preferred
    return context.get("detected_mood", "neutral") or "neutral"


def _write_log(result: SelectionResult, context: dict) -> None:
    try:
        save_context_log(
            time_period=context.get("time_period", ""),
            detected_mood=context.get("detected_mood", ""),
            image_id=result.image.get("id") if result.image else None,
            selection_score=result.total_score,
            score_breakdown=result.breakdown,
            matched_tags=result.matched_tags,
            reasoning_text=result.reasoning_text,
            was_override=result.was_override,
        )
    except Exception as exc:
        logger.error("Failed to write context log: %s", exc)
