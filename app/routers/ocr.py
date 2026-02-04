"""
OCR Router Module

This module provides the /read-handwriting endpoint for OCR processing.
It integrates OCRService, FileValidator, MetricsService, ModelRegistry, and rate limiting
to provide a secure, monitored, and performant OCR API with dynamic model discovery.

Validates: Requirements 1.5, 2.1, 2.2
"""

import time
from fastapi import APIRouter, Depends, File, UploadFile, Request, HTTPException
from app.services.ocr_service import OCRService
from app.services.metrics_service import MetricsService
from app.services.model_registry import ModelRegistry
from app.utils.validators import FileValidator
from app.models.responses import OCRResponse, ErrorResponse
from app.config import Settings, get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="",
    tags=["OCR"]
)


# Singleton instances
_ocr_service_instance = None
_file_validator_instance = None
_metrics_service_instance = None
_model_registry_instance = None


def get_model_registry(settings: Settings = Depends(get_settings)) -> ModelRegistry:
    """
    Dependency injection for ModelRegistry.
    
    Returns a singleton instance of ModelRegistry for dynamic model discovery.
    
    Args:
        settings: Application settings
        
    Returns:
        ModelRegistry: Singleton model registry instance
    """
    global _model_registry_instance
    if _model_registry_instance is None:
        _model_registry_instance = ModelRegistry(settings)
    return _model_registry_instance


def get_ocr_service(
    settings: Settings = Depends(get_settings),
    model_registry: ModelRegistry = Depends(get_model_registry)
) -> OCRService:
    """
    Dependency injection for OCRService.
    
    Returns a singleton instance of OCRService to reuse HTTP client connections.
    Now includes ModelRegistry for dynamic model discovery.
    
    Args:
        settings: Application settings
        model_registry: Model registry for dynamic model discovery
        
    Returns:
        OCRService: Singleton OCR service instance
    """
    global _ocr_service_instance
    if _ocr_service_instance is None:
        _ocr_service_instance = OCRService(settings, model_registry)
    return _ocr_service_instance


def get_file_validator(settings: Settings = Depends(get_settings)) -> FileValidator:
    """
    Dependency injection for FileValidator.
    
    Args:
        settings: Application settings
        
    Returns:
        FileValidator: File validator instance
    """
    global _file_validator_instance
    if _file_validator_instance is None:
        _file_validator_instance = FileValidator(settings)
    return _file_validator_instance


def get_metrics_service() -> MetricsService:
    """
    Dependency injection for MetricsService.
    
    Returns a singleton instance of MetricsService to ensure all requests
    use the same metrics collector.
    
    Returns:
        MetricsService: Singleton metrics service instance
    """
    global _metrics_service_instance
    if _metrics_service_instance is None:
        _metrics_service_instance = MetricsService()
    return _metrics_service_instance


@router.post(
    "/read-handwriting",
    response_model=OCRResponse,
    summary="Extract Handwritten Text",
    description="""
    Extract handwritten text from an uploaded image using OCR.
    
    This endpoint:
    - Accepts image files (JPEG, PNG, WebP) up to 10MB
    - Processes images asynchronously for optimal performance
    - Returns extracted text with confidence score and processing time
    - Applies rate limiting (10 requests per minute per IP) - configured at app level
    - Tracks performance metrics
    
    **Rate Limit:** 10 requests per minute per IP address (enforced by slowapi middleware)
    
    **Supported Formats:** JPEG, PNG, WebP
    
    **Maximum File Size:** 10MB
    
    **Note:** Rate limiting is applied via the slowapi limiter decorator at the 
    application level in main.py. The limiter will automatically return 429 status
    with retry-after headers when limits are exceeded.
    """,
    responses={
        200: {
            "description": "OCR processing completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "text": "Hello World",
                        "confidence": 0.95,
                        "processing_time": 2.34,
                        "model_used": "qwen/qwen2.5-vl-72b-instruct:free",
                        "language": None
                    }
                }
            }
        },
        400: {
            "description": "Invalid file (wrong type, too large, or empty)",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Validation Error",
                        "detail": "File too large (15.5MB). Maximum allowed size: 10MB",
                        "timestamp": "2024-01-01T12:00:00.000000",
                        "path": "/read-handwriting"
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Rate Limit Exceeded",
                        "detail": "Too many requests. Please retry after 60 seconds.",
                        "timestamp": "2024-01-01T12:00:00.000000",
                        "path": "/read-handwriting"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        },
        502: {
            "description": "External API error",
            "model": ErrorResponse
        },
        504: {
            "description": "OCR processing timeout",
            "model": ErrorResponse
        }
    }
)
async def read_handwriting(
    request: Request,
    file: UploadFile = File(..., description="Image file containing handwritten text"),
    language: str = None,
    ocr_service: OCRService = Depends(get_ocr_service),
    file_validator: FileValidator = Depends(get_file_validator),
    metrics_service: MetricsService = Depends(get_metrics_service),
    settings: Settings = Depends(get_settings)
) -> OCRResponse:
    """
    Extract handwritten text from an uploaded image.
    
    This endpoint performs the following steps:
    1. Applies rate limiting (10 requests per minute per IP)
    2. Validates the uploaded file (type, size, content)
    3. Processes the image asynchronously using OCR service
    4. Records performance metrics
    5. Returns extracted text with metadata
    
    Args:
        request: FastAPI request object (for rate limiting)
        file: Uploaded image file
        language: Optional language hint for OCR (e.g., 'Turkish', 'English')
        ocr_service: Injected OCR service instance
        file_validator: Injected file validator instance
        metrics_service: Injected metrics service instance
        settings: Application settings
        
    Returns:
        OCRResponse: Extracted text with confidence, processing time, and model info
        
    Raises:
        HTTPException: 
            - 400: Invalid file (wrong type, too large, or empty)
            - 429: Rate limit exceeded
            - 500: Internal server error
            - 502: External API error
            - 504: OCR processing timeout
            
    Example:
        >>> # Upload an image file
        >>> files = {"file": ("handwriting.jpg", image_bytes, "image/jpeg")}
        >>> response = requests.post("/read-handwriting", files=files)
        >>> print(response.json()["text"])
        "Hello World"
    """
    
    start_time = time.time()
    success = False
    
    try:
        logger.info(
            "OCR request received",
            filename=file.filename,
            content_type=file.content_type,
            language=language
        )
        
        # Step 1: Validate uploaded file
        file_bytes = await file_validator.validate_image_file(file)
        
        logger.info(
            "File validation successful",
            filename=file.filename,
            size_bytes=len(file_bytes)
        )
        
        # Step 2: Process image with OCR service (with fallback)
        try:
            extracted_text, confidence, processing_time, model_used = await ocr_service.process_handwriting(
                image_bytes=file_bytes,
                language=language
            )
            
            success = True
            
            logger.info(
                "OCR processing successful",
                text_length=len(extracted_text),
                confidence=confidence,
                processing_time=processing_time,
                model_used=model_used
            )
            
            # Step 3: Record metrics
            await metrics_service.record_request(
                endpoint="/read-handwriting",
                response_time=processing_time,
                success=True
            )
            
            # Step 4: Return response
            return OCRResponse(
                text=extracted_text,
                confidence=confidence,
                processing_time=processing_time,
                model_used=model_used,
                language=language
            )
            
        except TimeoutError as e:
            # OCR timeout - return 504
            logger.error(
                "OCR processing timeout",
                timeout=settings.ocr_timeout_seconds,
                error=str(e)
            )
            raise HTTPException(
                status_code=504,
                detail=f"OCR processing timeout after {settings.ocr_timeout_seconds} seconds"
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (from external API)
            raise
            
        except Exception as e:
            # External API error - return 502
            logger.error(
                "External API error",
                error=str(e),
                exc_info=True
            )
            raise HTTPException(
                status_code=502,
                detail=f"External API error: {str(e)}"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, etc.)
        success = False
        raise
        
    except Exception as e:
        # Unexpected error - return 500
        success = False
        logger.error(
            "Unexpected error in OCR endpoint",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
    finally:
        # Record metrics even if request failed
        if not success:
            total_time = time.time() - start_time
            await metrics_service.record_request(
                endpoint="/read-handwriting",
                response_time=total_time,
                success=False
            )
