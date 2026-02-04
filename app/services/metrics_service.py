"""
Metrics Service for collecting and reporting performance metrics.

This module provides the MetricsService class that tracks request counts,
response times, error rates, and other performance metrics for API endpoints.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List
import asyncio


@dataclass
class EndpointMetrics:
    """
    Metrics data for a single endpoint.
    
    Attributes:
        total_requests: Total number of requests received
        successful_requests: Number of successful requests (2xx status)
        failed_requests: Number of failed requests (4xx, 5xx status)
        total_response_time: Cumulative response time in seconds
        response_times: List of individual response times for detailed analysis
    """
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    
    @property
    def average_response_time(self) -> float:
        """
        Calculate average response time.
        
        Returns:
            Average response time in seconds, or 0.0 if no requests
        """
        return self.total_response_time / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """
        Calculate error rate as a ratio.
        
        Returns:
            Error rate (0.0 to 1.0), or 0.0 if no requests
        """
        return self.failed_requests / self.total_requests if self.total_requests > 0 else 0.0


class MetricsService:
    """
    Service for collecting and reporting performance metrics.
    
    This service provides thread-safe metrics collection using async locks.
    It tracks per-endpoint metrics including request counts, response times,
    and error rates.
    
    Attributes:
        metrics: Dictionary mapping endpoint names to their metrics
        start_time: Service start timestamp for uptime calculation
        _lock: Async lock for thread-safe operations
    """
    
    def __init__(self):
        """Initialize the metrics service."""
        self.metrics: Dict[str, EndpointMetrics] = {}
        self.start_time = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()
    
    async def record_request(
        self, 
        endpoint: str, 
        response_time: float, 
        success: bool
    ) -> None:
        """
        Record a request metric for an endpoint.
        
        This method is thread-safe and can be called concurrently from
        multiple requests.
        
        Args:
            endpoint: The endpoint path (e.g., "/read-handwriting")
            response_time: Response time in seconds
            success: True if request was successful (2xx status), False otherwise
        """
        async with self._lock:
            if endpoint not in self.metrics:
                self.metrics[endpoint] = EndpointMetrics()
            
            metric = self.metrics[endpoint]
            metric.total_requests += 1
            metric.total_response_time += response_time
            metric.response_times.append(response_time)
            
            if success:
                metric.successful_requests += 1
            else:
                metric.failed_requests += 1
    
    async def get_metrics(self) -> Dict:
        """
        Get all collected metrics.
        
        Returns:
            Dictionary containing:
                - uptime_seconds: Service uptime in seconds
                - endpoints: Per-endpoint metrics including:
                    - total_requests: Total request count
                    - successful_requests: Successful request count
                    - failed_requests: Failed request count
                    - average_response_time: Average response time in seconds
                    - error_rate: Error rate (0.0 to 1.0)
        """
        async with self._lock:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            
            return {
                "uptime_seconds": uptime,
                "endpoints": {
                    endpoint: {
                        "total_requests": m.total_requests,
                        "successful_requests": m.successful_requests,
                        "failed_requests": m.failed_requests,
                        "average_response_time": m.average_response_time,
                        "error_rate": m.error_rate
                    }
                    for endpoint, m in self.metrics.items()
                }
            }
    
    async def reset_metrics(self) -> None:
        """
        Reset all metrics and restart uptime counter.
        
        This method clears all collected metrics and resets the start time.
        Useful for testing or periodic metric resets.
        """
        async with self._lock:
            self.metrics.clear()
            self.start_time = datetime.now(timezone.utc)
