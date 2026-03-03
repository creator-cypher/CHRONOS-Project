"""
Chronos — Cloudinary Upload Service
=====================================

Handles all image uploads to Cloudinary.  Returns a persistent HTTPS URL
that is stored in images.image_url and used directly as a CSS background —
no local file storage required.

Configuration is read from CLOUDINARY_URL in .env:
    CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME

The Cloudinary library auto-parses that format via cloudinary.config().
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy init — configure once on first call, not at import time
# ---------------------------------------------------------------------------

_configured = False


def _ensure_configured() -> bool:
    """
    Configures the Cloudinary library from CLOUDINARY_URL env var.
    Returns True if configured successfully, False if the key is missing.
    """
    global _configured
    if _configured:
        return True

    url = os.environ.get("CLOUDINARY_URL", "")
    if not url:
        logger.warning("CLOUDINARY_URL not set — uploads will fail.")
        return False

    try:
        import cloudinary
        cloudinary.config.from_url(url)
        _configured = True
        return True
    except Exception as exc:
        logger.error("Cloudinary config failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_image(source: bytes | str | Path, filename: str = "") -> dict:
    """
    Uploads an image to Cloudinary and returns a result dict.

    Parameters
    ----------
    source   : raw bytes, local file path, or HTTPS URL
    filename : used as the Cloudinary public_id base (optional)

    Returns
    -------
    {
        "success":      bool,
        "secure_url":   str,   # permanent HTTPS URL (empty on failure)
        "public_id":    str,   # Cloudinary asset ID
        "width":        int,
        "height":       int,
        "format":       str,
        "error":        str,   # non-empty only on failure
    }
    """
    if not _ensure_configured():
        return _err("CLOUDINARY_URL not configured in environment.")

    try:
        import cloudinary.uploader

        # Build upload kwargs
        kwargs: dict = {
            "folder":         "chronos",
            "resource_type":  "image",
            # Auto-convert to WebP for smaller payloads; fallback to original
            "format":         "webp",
            # Eager transformation: cap at 2400 px wide, quality auto
            "transformation": [{"width": 2400, "crop": "limit", "quality": "auto"}],
            "overwrite":      False,
        }

        if filename:
            # Use filename stem (no extension) as the public_id hint
            stem = Path(filename).stem[:80]  # Cloudinary limit
            kwargs["public_id"] = f"chronos/{stem}"

        # Accept bytes, Path, or string (URL / local path)
        if isinstance(source, bytes):
            result = cloudinary.uploader.upload(source, **kwargs)
        elif isinstance(source, Path):
            result = cloudinary.uploader.upload(str(source), **kwargs)
        else:
            result = cloudinary.uploader.upload(source, **kwargs)

        return {
            "success":    True,
            "secure_url": result.get("secure_url", ""),
            "public_id":  result.get("public_id", ""),
            "width":      result.get("width", 0),
            "height":     result.get("height", 0),
            "format":     result.get("format", ""),
            "error":      "",
        }

    except Exception as exc:
        logger.error("Cloudinary upload failed: %s", exc, exc_info=True)
        return _err(str(exc))


def delete_image(public_id: str) -> bool:
    """
    Deletes an image from Cloudinary by its public_id.
    Used when an image is deactivated/removed from the library.
    Returns True on success, False on failure (never raises).
    """
    if not _ensure_configured():
        return False
    try:
        import cloudinary.uploader
        cloudinary.uploader.destroy(public_id, resource_type="image")
        return True
    except Exception as exc:
        logger.error("Cloudinary delete failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _err(message: str) -> dict:
    return {
        "success": False, "secure_url": "", "public_id": "",
        "width": 0, "height": 0, "format": "", "error": message,
    }
