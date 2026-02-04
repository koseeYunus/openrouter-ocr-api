"""
OCR Service Module

This module provides the OCRService class for processing handwriting images
using the OpenRouter API with async operations and multi-model fallback.

Validates: Requirements 2.1, 2.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import base64
import time
from typing import Tuple, Optional, TYPE_CHECKING
from httpx import AsyncClient, TimeoutException, HTTPStatusError, ConnectError, ReadTimeout
from app.config import Settings
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.services.model_registry import ModelRegistry

logger = get_logger(__name__)


class ModelFailureError(Exception):
    """Exception raised when a model fails to process the request."""
    pass


class OCRService:
    """
    Asynchronous OCR service for processing handwriting images.
    
    This service handles:
    - Image encoding to base64
    - OpenRouter API integration
    - Timeout management
    - Error handling and logging
    - Processing time measurement
    - Confidence score calculation
    
    Attributes:
        settings: Application settings
        client: Async HTTP client for API calls
    """
    
    def __init__(self, settings: Settings, model_registry: Optional['ModelRegistry'] = None):
        """
        Initialize OCR service with configuration.
        
        Args:
            settings: Application settings containing API credentials and timeouts
            model_registry: Optional model registry for dynamic model discovery
        """
        self.settings = settings
        self.model_registry = model_registry
        self.client = AsyncClient(
            base_url=settings.openrouter_base_url,
            timeout=settings.ocr_timeout_seconds,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/openrouter-ocr-api",
                "X-Title": "Handwriting OCR Service"
            }
        )
        
        if model_registry:
            logger.info("OCRService initialized with dynamic model registry")
        else:
            logger.info(
                "OCRService initialized with static models",
                models=settings.ocr_model_fallback_list,
                timeout=settings.ocr_timeout_seconds
            )
    
    async def encode_image(self, image_bytes: bytes) -> str:
        """
        Encode image bytes to base64 string.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Base64 encoded string
        """
        return base64.b64encode(image_bytes).decode("utf-8")
    
    async def process_handwriting(
        self, 
        image_bytes: bytes,
        language: Optional[str] = None
    ) -> Tuple[str, float, float, str]:
        """
        Process handwriting image with multi-model fallback mechanism.
        
        This method attempts to process the image using a prioritized list of models.
        If a model fails (4xx/5xx error, timeout, or empty response), it automatically
        tries the next model in the list. If using ModelRegistry, it will automatically
        refresh the model list on 404 errors.
        
        Args:
            image_bytes: Raw image bytes to process
            language: Optional language hint for OCR (e.g., 'Turkish', 'English')
            
        Returns:
            Tuple containing:
                - extracted_text: The transcribed text from the image
                - confidence_score: Confidence score (0.0 to 1.0)
                - processing_time: Time taken to process in seconds
                - model_used: The model that successfully processed the request
                
        Raises:
            Exception: If all models fail to process the request
        """
        start_time = time.time()
        
        # Get available models (dynamic or static)
        if self.model_registry:
            model_list = await self.model_registry.get_available_models()
        else:
            model_list = self.settings.ocr_model_fallback_list
        
        logger.info(
            "Starting OCR processing with fallback",
            image_size=len(image_bytes),
            language=language,
            models=model_list,
            dynamic=self.model_registry is not None
        )
        
        # Encode image once (reuse for all model attempts)
        base64_image = await self.encode_image(image_bytes)
        
        # Try each model in the fallback list
        last_error = None
        models_tried = []
        
        for model_id in model_list:
            models_tried.append(model_id)
            
            try:
                logger.info(f"Attempting OCR with model: {model_id}")
                
                extracted_text, confidence, model_processing_time = await self._process_with_model(
                    base64_image=base64_image,
                    model_id=model_id,
                    language=language
                )
                
                total_processing_time = time.time() - start_time
                
                logger.info(
                    "OCR processing successful",
                    model_used=model_id,
                    text_length=len(extracted_text),
                    confidence=confidence,
                    processing_time=total_processing_time
                )
                
                return extracted_text, confidence, total_processing_time, model_id
                
            except HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code
                
                logger.warning(
                    f"Model {model_id} failed, trying next model",
                    model=model_id,
                    error_type="HTTPStatusError",
                    error_message=str(e),
                    status_code=status_code
                )
                
                # Handle 404 specifically - model not found
                if status_code == 404 and self.model_registry:
                    logger.warning(
                        "Model 404 detected, refreshing model list",
                        failed_model=model_id
                    )
                    # Refresh model list and get updated models
                    updated_models = await self.model_registry.handle_model_404(model_id)
                    # Add any new models we haven't tried yet
                    for new_model in updated_models:
                        if new_model not in models_tried and new_model not in model_list:
                            model_list.append(new_model)
                            logger.info(f"Added new model to try: {new_model}")
                
                continue
                
            except (TimeoutException, ReadTimeout, ConnectError, ModelFailureError) as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)
                
                logger.warning(
                    f"Model {model_id} failed, trying next model",
                    model=model_id,
                    error_type=error_type,
                    error_message=error_msg
                )
                
                continue
        
        # All models failed
        total_processing_time = time.time() - start_time
        logger.error(
            "All models failed to process the image",
            models_tried=models_tried,
            total_processing_time=total_processing_time,
            last_error=str(last_error)
        )
        
        raise Exception(
            f"All OCR models failed. Last error: {str(last_error)}"
        )
    
    async def _process_with_model(
        self,
        base64_image: str,
        model_id: str,
        language: Optional[str] = None
    ) -> Tuple[str, float, float]:
        """
        Process image with a specific model.
        
        Args:
            base64_image: Base64 encoded image
            model_id: Model identifier to use
            language: Optional language hint
            
        Returns:
            Tuple of (extracted_text, confidence, processing_time)
            
        Raises:
            HTTPStatusError: If API returns 4xx/5xx error
            TimeoutException: If request times out
            ModelFailureError: If response is empty or invalid
        """
        start_time = time.time()
        
        # Build prompt based on language
        prompt = self._build_prompt(language)
        
        # Prepare request payload
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        }
        
        # Send async request to OpenRouter API
        response = await self.client.post(
            "/chat/completions",
            json=payload
        )
        
        # Raise exception for error status codes (4xx, 5xx)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Validate response structure
        if "choices" not in data or len(data["choices"]) == 0:
            raise ModelFailureError(f"Empty or invalid response from model {model_id}")
        
        # Extract text from response
        extracted_text = data["choices"][0]["message"]["content"].strip()
        
        # Check if text is empty
        if not extracted_text:
            raise ModelFailureError(f"Model {model_id} returned empty text")
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Calculate confidence score
        confidence = self._calculate_confidence(data, extracted_text)
        
        return extracted_text, confidence, processing_time
    
    def _build_prompt(self, language: Optional[str]) -> str:
        """
        Build OCR prompt based on language parameter.
        
        Args:
            language: Optional language hint
            
        Returns:
            Formatted prompt string
        """
        base_prompt = "Please transcribe the handwritten text in this image strictly."
        
        if language:
            base_prompt += f" The text is in {language}."
        
        base_prompt += " Return only the text found, do not add any conversational phrases."
        
        return base_prompt
    
    def _calculate_confidence(self, response_data: dict, extracted_text: str) -> float:
        """
        Calculate confidence score for OCR result.
        
        This is a simplified implementation. In production, this could be enhanced
        with actual model confidence scores if available from the API.
        
        Args:
            response_data: Full API response data
            extracted_text: Extracted text from response
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence
        confidence = 0.95
        
        # Reduce confidence if text is very short (might be uncertain)
        if len(extracted_text) < 5:
            confidence = 0.85
        
        # Check if response includes finish_reason
        if "choices" in response_data and len(response_data["choices"]) > 0:
            finish_reason = response_data["choices"][0].get("finish_reason")
            if finish_reason != "stop":
                confidence = 0.80
        
        return confidence
    
    async def close(self):
        """
        Close the HTTP client and cleanup resources.
        
        This should be called during application shutdown to ensure
        proper cleanup of connections.
        """
        await self.client.aclose()
        logger.info("OCRService closed")
