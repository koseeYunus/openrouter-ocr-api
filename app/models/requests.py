"""
Request Models Module

This module defines Pydantic models for API requests including OCR requests
and health check requests.

Validates: Requirements 12.6
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class OCRRequest(BaseModel):
    """
    OCR request parameters model.
    
    This model defines optional parameters that can be sent with OCR requests
    for future extensions and enhanced functionality.
    
    Validates: Requirements 7.4
    """
    language: Optional[str] = Field(
        None,
        description="Target language for OCR (e.g., 'Turkish', 'English')",
        examples=["Turkish", "English", "Spanish", "French"]
    )
    enhance_image: Optional[bool] = Field(
        False,
        description="Apply image enhancement before OCR"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "language": "Turkish",
                "enhance_image": False
            }
        }
    )


class HealthCheckRequest(BaseModel):
    """
    Health check request parameters model.
    
    This model defines optional parameters for health check requests
    to allow for detailed health checks.
    """
    detailed: Optional[bool] = Field(
        False,
        description="Include detailed system information in health check"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detailed": True
            }
        }
    )
