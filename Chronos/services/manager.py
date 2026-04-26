"""
Chronos — Service Manager (Orchestration Layer)
===============================================
This module acts as the single point of entry for the UI. It coordinates 
between the database, logic modules, and external services.
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from database.queries import (
    get_analyzed_images, get_preferences, save_context_log, 
    update_image_display_stats, add_image, update_image_analysis
)
from logic.context import get_current_context
from logic.engine import select_best_image
from services.vision import analyze_image
from services.cloudinary_upload import upload_image as cloudinary_upload

logger = logging.getLogger(__name__)

class ChronosManager:
    @staticmethod
    def get_next_display_state(user_id: str = "", profile_type: str = "Standard") -> Optional[Any]:
        """
        Orchestrates the selection of the next image to display.
        This is the single entry point for image selection logic.
        """
        # 1. Context detection
        context = get_current_context()
        
        # 2. Call Decision Engine
        # The engine handles its own logging and stats internally.
        result = select_best_image(context, user_id=user_id, profile_type=profile_type)
        
        return result

    @staticmethod
    def process_new_upload(file_bytes: bytes, title: str, user_id: str = "", profile_type: str = "Standard") -> Dict[str, Any]:
        """
        Orchestrates the full upload pipeline:
        1. Upload to Cloudinary.
        2. Add placeholder record to DB.
        3. Analyze with Gemini Vision.
        4. Apply safety filters based on profile_type.
        5. Update record with metadata.
        """
        from database.queries import hard_delete_image
        from services.cloudinary_upload import delete_image as cloudinary_delete
        
        try:
            # 1. Cloudinary
            upload_result = cloudinary_upload(file_bytes, folder="chronos")
            if not upload_result.get("secure_url"):
                return {"success": False, "error": "Cloudinary upload failed."}
            
            image_url = upload_result["secure_url"]
            public_id = upload_result.get("public_id", "")
            
            # 2. DB Placeholder
            image_id = add_image(title=title, image_url=image_url, user_id=user_id)
            
            # 3. Vision Analysis
            analysis = analyze_image(file_bytes)
            if not analysis.success:
                return {
                    "success": True, 
                    "image_id": image_id, 
                    "warning": f"Image uploaded but analysis failed: {analysis.error_message}"
                }
            
            # 4. Safety Filter (Kids Mode)
            if profile_type == "Kids" and not analysis.kids_safe:
                hard_delete_image(image_id)
                if public_id:
                    cloudinary_delete(public_id)
                return {"success": False, "error": "Blocked: Image not suitable for Kids mode."}

            # 5. Update DB
            update_image_analysis(
                image_id=image_id,
                description=analysis.description,
                primary_mood=analysis.primary_mood,
                optimal_time=analysis.optimal_time,
                base_score=analysis.base_score,
                dominant_colors=analysis.dominant_colors,
                tags=analysis.tags
            )
            
            return {"success": True, "image_id": image_id, "url": image_url}
            
        except Exception as e:
            logger.error(f"Upload pipeline failed: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def process_url_upload(url: str, user_id: str = "", profile_type: str = "Standard") -> Dict[str, Any]:
        """
        Orchestrates adding an image via URL:
        1. Validate URL.
        2. Add to DB.
        3. Analyze with Gemini.
        4. Apply safety filters.
        """
        from database.queries import hard_delete_image
        
        try:
            # 1. DB Record
            title = url.split("/")[-1][:60] or url[:40]
            image_id = add_image(title=title, image_url=url, user_id=user_id)
            
            # 2. Vision Analysis
            analysis = analyze_image(url)
            if not analysis.success:
                return {"success": True, "image_id": image_id, "warning": "URL added, analysis failed."}
                
            # 3. Safety Filter
            if profile_type == "Kids" and not analysis.kids_safe:
                hard_delete_image(image_id)
                return {"success": False, "error": "Blocked: URL not suitable for Kids mode."}
                
            # 4. Update DB
            update_image_analysis(
                image_id=image_id,
                description=analysis.description,
                primary_mood=analysis.primary_mood,
                optimal_time=analysis.optimal_time,
                base_score=analysis.base_score,
                dominant_colors=analysis.dominant_colors,
                tags=analysis.tags
            )
            
            return {"success": True, "image_id": image_id}
            
        except Exception as e:
            logger.error(f"URL import failed: {e}")
            return {"success": False, "error": str(e)}
