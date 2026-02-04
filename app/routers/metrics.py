"""
Metrics Router Module

This module provides the /metrics endpoint for performance monitoring.
It uses the MetricsService to collect and report request counts, response times,
error rates, and other performance statistics.

Validates: Requirements 1.2, 5.5
"""

from fastapi import APIRouter, Depends
from app.services.metrics_service import MetricsService
from app.models.responses import MetricsResponse


router = APIRouter(
    prefix="",
    tags=["Metrics"]
)


# Singleton instance of MetricsService
_metrics_service_instance = None


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


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Performance Metrics",
    description="""
    Performance metrics endpoint that provides:
    - Service uptime in seconds
    - Per-endpoint request statistics
    - Average response times
    - Error rates and success/failure counts
    
    Returns comprehensive performance metrics for monitoring and analysis.
    """,
    responses={
        200: {
            "description": "Metrics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "uptime_seconds": 3600.0,
                        "endpoints": {
                            "/read-handwriting": {
                                "total_requests": 100,
                                "successful_requests": 95,
                                "failed_requests": 5,
                                "average_response_time": 2.5,
                                "error_rate": 0.05
                            },
                            "/health": {
                                "total_requests": 50,
                                "successful_requests": 50,
                                "failed_requests": 0,
                                "average_response_time": 0.05,
                                "error_rate": 0.0
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
) -> dict:
    """
    Get performance metrics.
    
    This endpoint returns:
    1. Service uptime since startup
    2. Per-endpoint statistics including:
       - Total request count
       - Successful request count
       - Failed request count
       - Average response time
       - Error rate
    
    Args:
        metrics_service: Injected MetricsService instance
        
    Returns:
        dict: Performance metrics with uptime and per-endpoint statistics
        
    Example:
        >>> response = await get_metrics(metrics_service)
        >>> response["uptime_seconds"]
        3600.0
    """
    return await metrics_service.get_metrics()
