"""
Health Router Module

This module provides the /health endpoint for service health monitoring.
It uses the HealthMonitor service to check API status, external API connectivity,
and system resources.

Validates: Requirements 1.1, 5.6, 5.7
"""

from fastapi import APIRouter, Depends
from app.services.health_service import HealthMonitor
from app.models.responses import HealthCheckResponse
from app.config import Settings, get_settings


router = APIRouter(
    prefix="",
    tags=["Health"]
)


def get_health_monitor(settings: Settings = Depends(get_settings)) -> HealthMonitor:
    """
    Dependency injection for HealthMonitor.
    
    Args:
        settings: Application settings
        
    Returns:
        HealthMonitor: Configured health monitor instance
    """
    return HealthMonitor(settings)


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="""
    Comprehensive health check endpoint that monitors:
    - API service status
    - External API (OpenRouter) connectivity
    - System resources (CPU and memory usage)
    
    Returns overall health status and detailed check results.
    """,
    responses={
        200: {
            "description": "Health check completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "checks": {
                            "api": {
                                "status": "healthy",
                                "message": "API is running"
                            },
                            "external_api": {
                                "status": "healthy",
                                "message": "External API is reachable"
                            },
                            "system": {
                                "status": "healthy",
                                "cpu_percent": 25.5,
                                "memory_percent": 45.2,
                                "memory_available_mb": 2048.5
                            }
                        },
                        "timestamp": "2024-01-01T12:00:00.000000"
                    }
                }
            }
        }
    }
)
async def health_check(
    health_monitor: HealthMonitor = Depends(get_health_monitor)
) -> dict:
    """
    Perform comprehensive health check.
    
    This endpoint checks:
    1. API service is running and responsive
    2. External API (OpenRouter) is reachable
    3. System resources are within acceptable limits
    
    Args:
        health_monitor: Injected HealthMonitor instance
        
    Returns:
        dict: Health check results with overall status and individual checks
        
    Example:
        >>> response = await health_check(health_monitor)
        >>> response["status"]
        "healthy"
    """
    return await health_monitor.check_health()
