"""
Rate Limiting Middleware

This module provides rate limiting functionality using slowapi to protect
the API from abuse and control resource consumption.

Features:
- IP-based rate limiting
- Configurable rate limits per endpoint
- Automatic retry-after header injection
- Integration with FastAPI

Requirements: 4.1, 4.2, 3.7
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from typing import Callable

from app.config import Settings


def get_rate_limiter(settings: Settings) -> Limiter:
    """
    Create and configure rate limiter with IP-based limiting.
    
    Args:
        settings: Application settings containing rate limit configuration
        
    Returns:
        Configured Limiter instance
        
    The limiter uses IP address as the key for rate limiting and applies
    default limits from settings. Individual endpoints can override these
    limits using the @limiter.limit() decorator.
    """
    return Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute}/minute"],
        storage_uri="memory://",  # In-memory storage for simplicity
        strategy="fixed-window"  # Fixed window strategy
    )


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    
    Args:
        request: The incoming request
        exc: The RateLimitExceeded exception
        
    Returns:
        JSONResponse with 429 status code and retry-after header
        
    This handler ensures that rate limit errors are returned in a consistent
    JSON format with appropriate headers for client retry logic.
    
    Validates: Requirements 3.7, 4.2
    """
    # Default retry after time (60 seconds)
    retry_after = 60
    rate_limit = "10"
    
    # Try to extract information from the exception's limit object
    if hasattr(exc, 'limit') and exc.limit:
        limit_obj = exc.limit
        if hasattr(limit_obj, 'amount'):
            rate_limit = str(limit_obj.amount)
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate Limit Exceeded",
            "detail": f"Too many requests. Please retry after {retry_after} seconds.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path)
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": rate_limit,
            "X-RateLimit-Reset": str(retry_after)
        }
    )


def create_rate_limit_decorator(limiter: Limiter, limit: str):
    """
    Create a custom rate limit decorator for specific endpoints.
    
    Args:
        limiter: The Limiter instance
        limit: Rate limit string (e.g., "10/minute", "100/hour")
        
    Returns:
        Decorator function that can be applied to FastAPI routes
        
    Example:
        ```python
        rate_limit_10_per_min = create_rate_limit_decorator(limiter, "10/minute")
        
        @app.post("/api/endpoint")
        @rate_limit_10_per_min
        async def endpoint(request: Request):
            return {"message": "success"}
        ```
    """
    def decorator(func: Callable) -> Callable:
        return limiter.limit(limit)(func)
    return decorator


# Predefined rate limit decorators for common use cases
def get_ocr_rate_limit(limiter: Limiter) -> Callable:
    """
    Get rate limit decorator for OCR endpoint (10 requests per minute).
    
    Args:
        limiter: The Limiter instance
        
    Returns:
        Decorator function for OCR endpoint
        
    Validates: Requirements 4.1
    """
    return create_rate_limit_decorator(limiter, "10/minute")


def get_metrics_rate_limit(limiter: Limiter) -> Callable:
    """
    Get rate limit decorator for metrics endpoint (60 requests per minute).
    
    Args:
        limiter: The Limiter instance
        
    Returns:
        Decorator function for metrics endpoint
    """
    return create_rate_limit_decorator(limiter, "60/minute")


def get_health_rate_limit(limiter: Limiter) -> Callable:
    """
    Get rate limit decorator for health endpoint (120 requests per minute).
    
    Args:
        limiter: The Limiter instance
        
    Returns:
        Decorator function for health endpoint
    """
    return create_rate_limit_decorator(limiter, "120/minute")
