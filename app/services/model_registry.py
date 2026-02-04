"""
Model Registry Service

This module provides dynamic model discovery and management for OpenRouter models.
It automatically fetches, filters, and prioritizes free vision models, making the
service resilient to model name changes and deprecations.

Features:
- Automatic discovery of free vision models
- Smart filtering and prioritization
- Caching with automatic refresh
- Error-triggered updates
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from httpx import AsyncClient, HTTPError
from app.config import Settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """
    Dynamic model registry that discovers and manages available OCR models.
    
    This service automatically:
    - Fetches available models from OpenRouter
    - Filters for free vision-capable models
    - Prioritizes models by quality and reliability
    - Caches results with automatic refresh
    - Updates on 404 errors
    """
    
    # Model family priorities (higher score = higher priority)
    # Optimized for OCR and handwriting recognition
    MODEL_PRIORITIES = {
        "google/gemini": 100,      # Best for OCR, fast and accurate
        "qwen/qwen2.5-vl": 95,     # Excellent for dense text and OCR
        "qwen/qwen2-vl": 90,       # Good OCR performance
        "qwen/qwen-vl": 85,        # Older but reliable
        "meta-llama/llama-3.2": 80,  # Good vision, reliable
        "nvidia/nemotron": 75,     # NVIDIA vision models
        "mistralai/pixtral": 70,   # Mistral vision
        "anthropic/claude-3": 65,  # Claude vision (if free)
        "openai/gpt-4": 60,        # OpenAI vision (if free)
    }
    
    # Vision-related keywords to identify vision models
    VISION_KEYWORDS = [
        "vision", "vl", "visual", "ocr", 
        "gemini",  # All Gemini models support vision
        "llama-3.2-11b", "llama-3.2-90b",  # Only these Llama variants
        "qwen2-vl", "qwen-vl", "qwen2.5-vl",  # Qwen vision models
        "pixtral",  # Mistral vision
        "claude-3",  # Claude 3 vision models
        "gpt-4-vision", "gpt-4o", "gpt-4-turbo",  # OpenAI vision
        "nemotron",  # NVIDIA vision models
    ]
    
    # Keywords that indicate NON-vision models (exclude these)
    NON_VISION_KEYWORDS = [
        "text-only", "chat", "code", "instruct"
    ]
    
    def __init__(self, settings: Settings):
        """
        Initialize the model registry.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.client = AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            }
        )
        
        # Cache management
        self._cached_models: List[str] = []
        self._last_fetch: Optional[datetime] = None
        self._cache_duration = timedelta(hours=24)  # Refresh every 24 hours
        self._fetch_lock = asyncio.Lock()
        
        logger.info("ModelRegistry initialized")
    
    async def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """
        Get list of available free vision models.
        
        This method returns cached models if available and fresh, otherwise
        fetches new models from OpenRouter.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            List of model IDs, prioritized by quality
        """
        # Check if cache is valid
        if not force_refresh and self._is_cache_valid():
            logger.info(
                "Returning cached models",
                count=len(self._cached_models),
                age_seconds=(datetime.now() - self._last_fetch).total_seconds()
            )
            return self._cached_models
        
        # Fetch new models (with lock to prevent concurrent fetches)
        async with self._fetch_lock:
            # Double-check cache after acquiring lock
            if not force_refresh and self._is_cache_valid():
                return self._cached_models
            
            logger.info(
                "Fetching models from OpenRouter",
                force_refresh=force_refresh
            )
            
            try:
                models = await self._fetch_and_filter_models()
                
                if models:
                    self._cached_models = models
                    self._last_fetch = datetime.now()
                    
                    logger.info(
                        "Models fetched and cached successfully",
                        count=len(models),
                        models=models[:5]  # Log first 5
                    )
                else:
                    logger.warning("No suitable models found, using fallback")
                    # If no models found, use configured fallback
                    if not self._cached_models:
                        self._cached_models = self.settings.ocr_model_fallback_list
                
                return self._cached_models
                
            except Exception as e:
                logger.error(
                    "Failed to fetch models from OpenRouter",
                    error=str(e),
                    exc_info=True
                )
                
                # Return cached models if available, otherwise use config
                if self._cached_models:
                    logger.warning("Using stale cached models due to fetch error")
                    return self._cached_models
                else:
                    logger.warning("Using configured fallback models")
                    return self.settings.ocr_model_fallback_list
    
    async def _fetch_and_filter_models(self) -> List[str]:
        """
        Fetch models from OpenRouter and filter for free vision models.
        
        Returns:
            List of filtered and prioritized model IDs
        """
        try:
            # Fetch all models
            response = await self.client.get("/models")
            response.raise_for_status()
            
            data = response.json()
            all_models = data.get("data", [])
            
            logger.info(f"Fetched {len(all_models)} total models from OpenRouter")
            
            # Filter and score models
            candidates = []
            
            for model in all_models:
                model_id = model.get("id", "")
                
                # Skip if no ID
                if not model_id:
                    continue
                
                # Check if free
                pricing = model.get("pricing", {})
                prompt_price = float(pricing.get("prompt", "1"))
                completion_price = float(pricing.get("completion", "1"))
                
                if prompt_price > 0 or completion_price > 0:
                    continue
                
                # Check if vision capable
                if not self._is_vision_model(model):
                    continue
                
                # Check if deprecated
                if model.get("deprecated", False):
                    logger.debug(f"Skipping deprecated model: {model_id}")
                    continue
                
                # Calculate priority score
                score = self._calculate_priority_score(model_id)
                
                candidates.append({
                    "id": model_id,
                    "score": score,
                    "name": model.get("name", ""),
                })
            
            # Sort by score (highest first)
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            # Extract model IDs
            model_ids = [c["id"] for c in candidates]
            
            logger.info(
                "Filtered models",
                total_found=len(model_ids),
                top_models=model_ids[:5]
            )
            
            return model_ids
            
        except HTTPError as e:
            logger.error(
                "HTTP error fetching models",
                status_code=getattr(e.response, "status_code", None),
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error fetching models",
                error=str(e),
                exc_info=True
            )
            raise
    
    def _is_vision_model(self, model: Dict[str, Any]) -> bool:
        """
        Check if a model is vision-capable for OCR tasks.
        
        Args:
            model: Model data from OpenRouter API
            
        Returns:
            True if model supports vision/images and is suitable for OCR
        """
        model_id = model.get("id", "").lower()
        model_name = model.get("name", "").lower()
        description = model.get("description", "").lower()
        
        # First, exclude non-vision models explicitly
        for keyword in self.NON_VISION_KEYWORDS:
            if keyword in model_id and "vision" not in model_id and "vl" not in model_id:
                return False
        
        # Check model ID for vision keywords (most reliable)
        has_vision_keyword = False
        for keyword in self.VISION_KEYWORDS:
            if keyword in model_id:
                has_vision_keyword = True
                break
        
        # If model ID has vision keyword, it's likely a vision model
        if has_vision_keyword:
            # Additional check: make sure it's not a text-only variant
            if "text" in model_id and "vision" not in model_id:
                return False
            return True
        
        # Check architecture modality (second most reliable)
        architecture = model.get("architecture", {})
        modality = architecture.get("modality", "")
        
        if isinstance(modality, str):
            modality_lower = modality.lower()
            # Look for explicit image support
            if "image" in modality_lower or "vision" in modality_lower:
                # Make sure it's input, not just output
                if "text+image" in modality_lower or "image->text" in modality_lower:
                    return True
        elif isinstance(modality, list):
            for mod in modality:
                mod_str = str(mod).lower()
                if "image" in mod_str or "vision" in mod_str:
                    return True
        
        # Check name and description as last resort
        vision_terms = ["vision", "visual", "image", "ocr", "multimodal"]
        for term in vision_terms:
            if term in model_name or term in description:
                # But make sure it's not just mentioned, actually supported
                if "support" in description or "multimodal" in description:
                    return True
        
        return False
    
    def _calculate_priority_score(self, model_id: str) -> int:
        """
        Calculate priority score for a model based on OCR performance.
        
        Higher scores indicate better models for OCR and handwriting recognition.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Priority score (higher is better)
        """
        score = 0
        model_id_lower = model_id.lower()
        
        # Check against priority families
        for family, family_score in self.MODEL_PRIORITIES.items():
            if model_id_lower.startswith(family.lower()):
                score += family_score
                break
        
        # Bonus for OCR-specific features
        if "vl" in model_id_lower:
            score += 15  # Vision-language models are good for OCR
        if "vision" in model_id_lower:
            score += 12  # Explicit vision support
        if "ocr" in model_id_lower:
            score += 20  # Specifically designed for OCR
        
        # Bonus for performance characteristics
        if "flash" in model_id_lower:
            score += 10  # Fast models
        if "instruct" in model_id_lower:
            score += 5  # Instruction-tuned
        if "72b" in model_id_lower or "90b" in model_id_lower:
            score += 8  # Larger models (better quality)
        if "2.5" in model_id_lower or "3.0" in model_id_lower:
            score += 7  # Newer versions
            
        # Penalties for less stable versions
        if "preview" in model_id_lower:
            score -= 5  # Preview versions less stable
        if "exp" in model_id_lower or "experimental" in model_id_lower:
            score -= 3  # Experimental versions
        if "beta" in model_id_lower:
            score -= 4  # Beta versions
        
        # Penalty for generic/auto models
        if model_id_lower == "openrouter/free" or model_id_lower == "openrouter/auto":
            score -= 20  # These are fallbacks, not primary choices
        
        return score
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached models are still valid.
        
        Returns:
            True if cache is valid and fresh
        """
        if not self._cached_models or not self._last_fetch:
            return False
        
        age = datetime.now() - self._last_fetch
        return age < self._cache_duration
    
    async def handle_model_404(self, failed_model_id: str) -> List[str]:
        """
        Handle a 404 error for a specific model.
        
        This triggers a force refresh of the model list and returns
        updated models excluding the failed one.
        
        Args:
            failed_model_id: Model ID that returned 404
            
        Returns:
            Updated list of available models
        """
        logger.warning(
            "Model 404 detected, forcing refresh",
            failed_model=failed_model_id
        )
        
        # Force refresh
        models = await self.get_available_models(force_refresh=True)
        
        # Remove the failed model from the list
        if failed_model_id in models:
            models = [m for m in models if m != failed_model_id]
            self._cached_models = models
            
            logger.info(
                "Removed failed model from cache",
                failed_model=failed_model_id,
                remaining_count=len(models)
            )
        
        return models
    
    async def close(self):
        """Close the HTTP client and cleanup resources."""
        await self.client.aclose()
        logger.info("ModelRegistry closed")
