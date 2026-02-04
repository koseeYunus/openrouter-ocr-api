"""
Response Models Module

This module defines Pydantic models for API responses including success
responses and error responses.

Validates: Requirements 3.6, 12.6
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    
    All API errors return this structured format with error type,
    detailed message, timestamp, and request path.
    
    Validates: Requirements 3.6
    """
    error: str = Field(
        ...,
        description="Error type or category",
        examples=["Validation Error", "Internal Server Error", "Bad Gateway"]
    )
    detail: str = Field(
        ...,
        description="Detailed error message",
        examples=["File too large. Maximum size: 10MB"]
    )
    timestamp: str = Field(
        ...,
        description="Error timestamp in ISO format",
        examples=["2024-01-01T12:00:00.000000"]
    )
    path: str = Field(
        ...,
        description="Request path where error occurred",
        examples=["/read-handwriting", "/health"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Validation Error",
                "detail": "File too large. Maximum size: 10MB",
                "timestamp": "2024-01-01T12:00:00.000000",
                "path": "/read-handwriting"
            }
        }
    )


class OCRResponse(BaseModel):
    """
    OCR processing response model.
    
    Validates: Requirements 7.5, 7.6
    """
    text: str = Field(
        ...,
        description="Extracted text from image"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    processing_time: float = Field(
        ...,
        ge=0.0,
        description="Processing time in seconds"
    )
    model_used: str = Field(
        ...,
        description="OCR model identifier"
    )
    language: Optional[str] = Field(
        None,
        description="Detected or specified language"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Hello World",
                "confidence": 0.95,
                "processing_time": 2.34,
                "model_used": "qwen/qwen2.5-vl-72b-instruct:free",
                "language": "English"
            }
        }
    )


class HealthCheckResponse(BaseModel):
    """
    Health check response model.
    
    Validates: Requirements 5.6, 5.7
    """
    status: str = Field(
        ...,
        description="Overall health status"
    )
    checks: dict = Field(
        ...,
        description="Individual health checks"
    )
    timestamp: str = Field(
        ...,
        description="Check timestamp"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "checks": {
                    "api": {"status": "healthy", "message": "API is running"},
                    "external_api": {"status": "healthy", "message": "External API is reachable"}
                },
                "timestamp": "2024-01-01T12:00:00.000000"
            }
        }
    )


class MetricsResponse(BaseModel):
    """
    Metrics response model.
    
    Validates: Requirements 5.5
    """
    uptime_seconds: float = Field(
        ...,
        description="Service uptime in seconds"
    )
    endpoints: dict = Field(
        ...,
        description="Per-endpoint metrics"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uptime_seconds": 3600.0,
                "endpoints": {
                    "/read-handwriting": {
                        "total_requests": 100,
                        "successful_requests": 95,
                        "failed_requests": 5,
                        "average_response_time": 2.5,
                        "error_rate": 0.05
                    }
                }
            }
        }
    )


class APIInfo(BaseModel):
    """
    API information response model.
    
    Validates: Requirements 1.3
    """
    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    endpoints: list[dict] = Field(..., description="Available endpoints")
    documentation: dict = Field(..., description="Documentation links")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Handwriting OCR Service",
                "version": "2.0.0",
                "description": "Modern FastAPI backend for handwriting OCR",
                "endpoints": [
                    {"path": "/", "method": "GET", "description": "API information"},
                    {"path": "/health", "method": "GET", "description": "Health check"}
                ],
                "documentation": {
                    "swagger": "/docs",
                    "redoc": "/redoc",
                    "openapi": "/openapi.json"
                }
            }
        }
    )
