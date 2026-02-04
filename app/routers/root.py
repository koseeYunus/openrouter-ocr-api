"""
Root Router Module

This module provides the / (root) endpoint that returns API information
and a list of available endpoints. It serves as the entry point for API discovery.

Validates: Requirements 1.3
"""

from fastapi import APIRouter, Depends
from app.config import Settings, get_settings


router = APIRouter(
    prefix="",
    tags=["Root"]
)


@router.get(
    "/",
    summary="API Information",
    description="""
    Root endpoint that provides API information and available endpoints.
    
    This endpoint returns:
    - API name and version
    - Description of the service
    - List of available endpoints with descriptions
    - Links to API documentation
    
    Use this endpoint to discover available API functionality.
    """,
    responses={
        200: {
            "description": "API information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "name": "Handwriting OCR Service",
                        "version": "2.0.0",
                        "description": "Modern FastAPI backend for handwriting OCR with async processing, monitoring, and security features",
                        "endpoints": [
                            {
                                "path": "/",
                                "method": "GET",
                                "description": "API information and available endpoints"
                            },
                            {
                                "path": "/health",
                                "method": "GET",
                                "description": "Health check endpoint with system monitoring"
                            },
                            {
                                "path": "/metrics",
                                "method": "GET",
                                "description": "Performance metrics and statistics"
                            },
                            {
                                "path": "/read-handwriting",
                                "method": "POST",
                                "description": "Extract handwritten text from images"
                            }
                        ],
                        "documentation": {
                            "swagger_ui": "/docs",
                            "redoc": "/redoc",
                            "openapi_schema": "/openapi.json"
                        }
                    }
                }
            }
        }
    }
)
async def root(settings: Settings = Depends(get_settings)) -> dict:
    """
    Get API information and available endpoints.
    
    This endpoint provides an overview of the API, including:
    1. Service name and version
    2. Brief description of functionality
    3. List of all available endpoints with their methods and descriptions
    4. Links to interactive API documentation
    
    Args:
        settings: Application settings (injected)
        
    Returns:
        dict: API information with name, version, description, endpoints, and documentation links
        
    Example:
        >>> response = await root(settings)
        >>> response["name"]
        "Handwriting OCR Service"
        >>> len(response["endpoints"])
        4
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Modern FastAPI backend for handwriting OCR with async processing, monitoring, and security features",
        "endpoints": [
            {
                "path": "/",
                "method": "GET",
                "description": "API information and available endpoints"
            },
            {
                "path": "/health",
                "method": "GET",
                "description": "Health check endpoint with system monitoring"
            },
            {
                "path": "/metrics",
                "method": "GET",
                "description": "Performance metrics and statistics"
            },
            {
                "path": "/read-handwriting",
                "method": "POST",
                "description": "Extract handwritten text from images"
            }
        ],
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        }
    }
