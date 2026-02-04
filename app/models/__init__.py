"""
Models Package

This package contains Pydantic models for API requests and responses.
"""

from app.models.requests import (
    OCRRequest,
    HealthCheckRequest
)

from app.models.responses import (
    ErrorResponse,
    OCRResponse,
    HealthCheckResponse,
    MetricsResponse,
    APIInfo
)

__all__ = [
    # Request models
    "OCRRequest",
    "HealthCheckRequest",
    # Response models
    "ErrorResponse",
    "OCRResponse",
    "HealthCheckResponse",
    "MetricsResponse",
    "APIInfo"
]
