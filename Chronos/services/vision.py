"""
Chronos — Gemini Vision Service
=================================

Adapted from AuraFrame/api/services.py — Django imports removed.
API key is read directly from the environment via python-dotenv.

Confirmed working model: gemini-2.5-flash
"""

import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"

MAX_RETRIES = 3

ANALYSIS_PROMPT = """
You are an expert art director for a luxury ambient display system called Chronos.
Analyse the provided image and return a JSON object with EXACTLY this structure:

{
  "description": "<2-3 sentence poetic description of the scene>",
  "primary_mood": "<one of: calm | energetic | melancholic | joyful | mysterious | neutral>",
  "optimal_time": "<one of: dawn | morning | afternoon | evening | night | any>",
  "base_score": <float 0.0-1.0 representing aesthetic quality>,
  "dominant_colors": ["#hexcode1", "#hexcode2", "#hexcode3"],
  "tags": [
    {"name": "<label>", "category": "<subject|mood|time|color|style|technical>", "confidence": <0.0-1.0>}
  ]
}

Generate 5-10 tags. Return ONLY the JSON — no markdown, no explanation.
""".strip()


def build_prompt(depth: str = "standard", focus: str = "", custom: str = "") -> str:
    """Build an analysis prompt with configurable depth and focus areas."""
    base = ANALYSIS_PROMPT
    if depth == "quick":
        base = base.replace("2-3 sentence", "1 sentence")
        base = base.replace("5-10 tags", "3-5 tags")
    if focus:
        areas = [a.strip() for a in focus.split(",") if a.strip()]
        if areas:
            base += f"\n\nFocus your analysis on: {', '.join(areas)}."
    if custom:
        base += f"\n\nAdditional instructions: {custom}"
    return base


@dataclass
class AnalysisResult:
    success:         bool       = False
    description:     str        = ""
    primary_mood:    str        = "neutral"
    optimal_time:    str        = "any"
    base_score:      float      = 0.5
    dominant_colors: list       = field(default_factory=list)
    tags:            list[dict] = field(default_factory=list)
    error_message:   str        = ""


def analyze_image(
    source: str | Path | bytes,
    depth: str = "standard",
    focus: str = "",
    custom: str = "",
) -> AnalysisResult:
    """
    Sends an image to Gemini 2.5 Flash and returns structured metadata.

    Accepts: local file path, HTTPS URL, or raw bytes.
    Returns: AnalysisResult (always — never raises).

    Retries up to MAX_RETRIES with exponential backoff on transient failures.
    Supports configurable analysis depth and focus via build_prompt().
    """
    import time as _time

    if not GEMINI_API_KEY:
        return AnalysisResult(success=False, error_message="GEMINI_API_KEY not set in .env")

    try:
        from google import genai
        from google.genai import types as gt
    except ImportError:
        return AnalysisResult(success=False, error_message="Run: pip install google-genai")

    prompt = build_prompt(depth, focus, custom)
    temperature = 0.1 if depth == "quick" else 0.2
    max_tokens = 2048 if depth == "quick" else 4096

    last_error = ""
    for attempt in range(MAX_RETRIES):
        try:
            client     = genai.Client(api_key=GEMINI_API_KEY)
            image_part = _build_part(source, gt)

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[image_part, prompt],
                config=gt.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens),
            )
            return _parse(response.text.strip())

        except Exception as exc:
            last_error = str(exc)
            logger.warning("Gemini attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES - 1:
                _time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s

    logger.error("Gemini call failed after %d retries: %s", MAX_RETRIES, last_error)
    return AnalysisResult(success=False, error_message=last_error)


def _build_part(source, gt):
    if isinstance(source, bytes):
        return gt.Part.from_bytes(data=source, mime_type="image/jpeg")

    source = str(source)
    if source.startswith("http://") or source.startswith("https://"):
        # from_uri only works for gs:// (Google Cloud Storage) URIs.
        # For arbitrary HTTPS URLs we must download the bytes ourselves.
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_bytes = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        mime = content_type if content_type.startswith("image/") else "image/jpeg"
        return gt.Part.from_bytes(data=img_bytes, mime_type=mime)

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Not found: {path}")

    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp"}
    mime = mime_map.get(path.suffix.lower(), "image/jpeg")
    return gt.Part.from_bytes(data=path.read_bytes(), mime_type=mime)


def _parse(raw: str) -> AnalysisResult:
    text = raw.strip()

    # Extract JSON object from anywhere in the response.
    # Handles: thinking tokens, markdown fences, preamble text.
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("_parse failed. Raw response was:\n%s", raw)
        return AnalysisResult(success=False, error_message=f"JSON parse error: {exc}")

    tags = []
    for t in data.get("tags", []):
        try:
            tags.append({
                "name":       str(t["name"]).lower().strip(),
                "category":   str(t.get("category", "subject")),
                "confidence": float(t.get("confidence", 1.0)),
            })
        except (KeyError, ValueError):
            pass

    return AnalysisResult(
        success=True,
        description=str(data.get("description", "")),
        primary_mood=str(data.get("primary_mood", "neutral")),
        optimal_time=str(data.get("optimal_time", "any")),
        base_score=float(data.get("base_score", 0.5)),
        dominant_colors=list(data.get("dominant_colors", [])),
        tags=tags,
    )
