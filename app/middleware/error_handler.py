"""
Error Handler Middleware Module

This module provides global exception handlers for FastAPI application.
Handles HTTPException, ValidationError, and general exceptions with
structured error responses and logging.

Validates: Requirements 3.2, 3.3, 3.6
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from datetime import datetime, UTC
import traceback
from typing import Union

from app.models.responses import ErrorResponse
from app.utils.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions.
    
    Catches HTTPException instances raised by FastAPI endpoints and
    returns structured error responses. Logs the error with context.
    
    Args:
        request: FastAPI request object
        exc: HTTPException instance
    
    Returns:
        JSONResponse: Structured error response
    
    Example:
        >>> raise HTTPException(status_code=400, detail="Invalid file type")
        # Returns: {"error": "Bad Request", "detail": "Invalid file type", ...}
    
    Validates: Requirements 3.2, 3.6
    """
    # Log the error with context
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=str(exc.detail),
        path=str(request.url.path),
        method=request.method,
        client_host=request.client.host if request.client else None
    )
    
    # Determine error type from status code
    error_type = _get_error_type_from_status(exc.status_code)
    
    # Create error response
    error_response = ErrorResponse(
        error=error_type,
        detail=str(exc.detail),
        timestamp=datetime.now(UTC).isoformat(),
        path=str(request.url.path)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Handle validation errors.
    
    Catches Pydantic validation errors from request body, query parameters,
    or path parameters and returns structured error responses with detailed
    validation error information.
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError or ValidationError instance
    
    Returns:
        JSONResponse: Structured error response with validation details
    
    Example:
        # Invalid request body
        # Returns: {"error": "Validation Error", "detail": "field required", ...}
    
    Validates: Requirements 3.2, 3.6
    """
    # Extract validation errors
    errors = exc.errors() if hasattr(exc, 'errors') else [{"msg": str(exc)}]
    
    # Format error details
    error_details = []
    for error in errors:
        loc = " -> ".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        error_details.append(f"{loc}: {msg}" if loc else msg)
    
    detail_str = "; ".join(error_details)
    
    # Log the validation error
    logger.warning(
        "Validation error occurred",
        path=str(request.url.path),
        method=request.method,
        errors=errors,
        client_host=request.client.host if request.client else None
    )
    
    # Create error response
    error_response = ErrorResponse(
        error="Validation Error",
        detail=detail_str,
        timestamp=datetime.now(UTC).isoformat(),
        path=str(request.url.path)
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    Catches all unhandled exceptions and returns a generic error response
    to avoid exposing internal implementation details. Logs the full
    exception with stack trace for debugging.
    
    Args:
        request: FastAPI request object
        exc: Exception instance
    
    Returns:
        JSONResponse: Generic error response
    
    Example:
        # Any unhandled exception
        # Returns: {"error": "Internal Server Error", "detail": "An unexpected error occurred", ...}
    
    Validates: Requirements 3.3, 3.5, 3.6
    """
    # Get stack trace
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    
    # Log the error with full stack trace (critical level)
    logger.error(
        "Unexpected exception occurred",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=str(request.url.path),
        method=request.method,
        client_host=request.client.host if request.client else None,
        stack_trace=tb_str,
        exc_info=True  # This ensures stack trace is included in logs
    )
    
    # Create generic error response (don't expose internal details)
    error_response = ErrorResponse(
        error="Internal Server Error",
        detail="An unexpected error occurred. Please try again later.",
        timestamp=datetime.now(UTC).isoformat(),
        path=str(request.url.path)
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


async def external_api_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle external API failures.
    
    Specifically handles exceptions from external API calls (like OpenRouter)
    and returns appropriate error responses with 502 Bad Gateway status.
    
    Args:
        request: FastAPI request object
        exc: Exception from external API call
    
    Returns:
        JSONResponse: Bad Gateway error response
    
    Validates: Requirements 3.3, 3.6
    """
    # Log the external API failure
    logger.error(
        "External API call failed",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=str(request.url.path),
        method=request.method,
        client_host=request.client.host if request.client else None,
        exc_info=True
    )
    
    # Create error response
    error_response = ErrorResponse(
        error="Bad Gateway",
        detail="External service is currently unavailable. Please try again later.",
        timestamp=datetime.now(UTC).isoformat(),
        path=str(request.url.path)
    )
    
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=error_response.model_dump()
    )


def _get_error_type_from_status(status_code: int) -> str:
    """
    Get human-readable error type from HTTP status code.
    
    Args:
        status_code: HTTP status code
    
    Returns:
        str: Human-readable error type
    """
    error_types = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        408: "Request Timeout",
        409: "Conflict",
        413: "Payload Too Large",
        415: "Unsupported Media Type",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout"
    }
    return error_types.get(status_code, f"HTTP {status_code}")


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with FastAPI application.
    
    This function should be called during application initialization to
    register all custom exception handlers.
    
    Args:
        app: FastAPI application instance
    
    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    
    Validates: Requirements 3.2, 3.3, 3.6
    """
    # Register HTTP exception handler
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Register validation exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # Register general exception handler (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered successfully")
