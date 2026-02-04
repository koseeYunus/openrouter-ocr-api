"""
Unit tests for MetricsService.

Tests the metrics collection functionality including request tracking,
response time calculation, error rate computation, and thread-safety.
"""

import pytest
import asyncio
from datetime import datetime
from app.services.metrics_service import MetricsService, EndpointMetrics


class TestEndpointMetrics:
    """Test cases for EndpointMetrics dataclass."""
    
    def test_initial_values(self):
        """Test that EndpointMetrics initializes with correct default values."""
        metrics = EndpointMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_response_time == 0.0
        assert metrics.response_times == []
    
    def test_average_response_time_with_requests(self):
        """Test average response time calculation with requests."""
        metrics = EndpointMetrics(
            total_requests=3,
            total_response_time=6.0
        )
        
        assert metrics.average_response_time == 2.0
    
    def test_average_response_time_without_requests(self):
        """Test average response time returns 0.0 when no requests."""
        metrics = EndpointMetrics()
        
        assert metrics.average_response_time == 0.0
    
    def test_error_rate_with_requests(self):
        """Test error rate calculation with requests."""
        metrics = EndpointMetrics(
            total_requests=10,
            failed_requests=2
        )
        
        assert metrics.error_rate == 0.2
    
    def test_error_rate_without_requests(self):
        """Test error rate returns 0.0 when no requests."""
        metrics = EndpointMetrics()
        
        assert metrics.error_rate == 0.0
    
    def test_error_rate_all_successful(self):
        """Test error rate is 0.0 when all requests are successful."""
        metrics = EndpointMetrics(
            total_requests=5,
            successful_requests=5,
            failed_requests=0
        )
        
        assert metrics.error_rate == 0.0
    
    def test_error_rate_all_failed(self):
        """Test error rate is 1.0 when all requests failed."""
        metrics = EndpointMetrics(
            total_requests=5,
            successful_requests=0,
            failed_requests=5
        )
        
        assert metrics.error_rate == 1.0


class TestMetricsService:
    """Test cases for MetricsService."""
    
    @pytest.fixture
    def metrics_service(self):
        """Create a fresh MetricsService instance for each test."""
        return MetricsService()
    
    @pytest.mark.asyncio
    async def test_initialization(self, metrics_service):
        """Test that MetricsService initializes correctly."""
        assert metrics_service.metrics == {}
        assert isinstance(metrics_service.start_time, datetime)
        assert metrics_service._lock is not None
    
    @pytest.mark.asyncio
    async def test_record_single_successful_request(self, metrics_service):
        """Test recording a single successful request."""
        await metrics_service.record_request("/test", 1.5, success=True)
        
        metrics = await metrics_service.get_metrics()
        endpoint_metrics = metrics["endpoints"]["/test"]
        
        assert endpoint_metrics["total_requests"] == 1
        assert endpoint_metrics["successful_requests"] == 1
        assert endpoint_metrics["failed_requests"] == 0
        assert endpoint_metrics["average_response_time"] == 1.5
        assert endpoint_metrics["error_rate"] == 0.0
    
    @pytest.mark.asyncio
    async def test_record_single_failed_request(self, metrics_service):
        """Test recording a single failed request."""
        await metrics_service.record_request("/test", 0.5, success=False)
        
        metrics = await metrics_service.get_metrics()
        endpoint_metrics = metrics["endpoints"]["/test"]
        
        assert endpoint_metrics["total_requests"] == 1
        assert endpoint_metrics["successful_requests"] == 0
        assert endpoint_metrics["failed_requests"] == 1
        assert endpoint_metrics["average_response_time"] == 0.5
        assert endpoint_metrics["error_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_record_multiple_requests_same_endpoint(self, metrics_service):
        """Test recording multiple requests to the same endpoint."""
        await metrics_service.record_request("/api/test", 1.0, success=True)
        await metrics_service.record_request("/api/test", 2.0, success=True)
        await metrics_service.record_request("/api/test", 1.5, success=False)
        
        metrics = await metrics_service.get_metrics()
        endpoint_metrics = metrics["endpoints"]["/api/test"]
        
        assert endpoint_metrics["total_requests"] == 3
        assert endpoint_metrics["successful_requests"] == 2
        assert endpoint_metrics["failed_requests"] == 1
        assert endpoint_metrics["average_response_time"] == 1.5  # (1.0 + 2.0 + 1.5) / 3
        assert endpoint_metrics["error_rate"] == pytest.approx(0.333, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_record_multiple_endpoints(self, metrics_service):
        """Test recording requests to multiple different endpoints."""
        await metrics_service.record_request("/endpoint1", 1.0, success=True)
        await metrics_service.record_request("/endpoint2", 2.0, success=True)
        await metrics_service.record_request("/endpoint1", 1.5, success=False)
        
        metrics = await metrics_service.get_metrics()
        
        assert len(metrics["endpoints"]) == 2
        assert "/endpoint1" in metrics["endpoints"]
        assert "/endpoint2" in metrics["endpoints"]
        
        endpoint1_metrics = metrics["endpoints"]["/endpoint1"]
        assert endpoint1_metrics["total_requests"] == 2
        assert endpoint1_metrics["successful_requests"] == 1
        assert endpoint1_metrics["failed_requests"] == 1
        
        endpoint2_metrics = metrics["endpoints"]["/endpoint2"]
        assert endpoint2_metrics["total_requests"] == 1
        assert endpoint2_metrics["successful_requests"] == 1
        assert endpoint2_metrics["failed_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_get_metrics_includes_uptime(self, metrics_service):
        """Test that get_metrics includes uptime_seconds."""
        # Wait a small amount of time
        await asyncio.sleep(0.1)
        
        metrics = await metrics_service.get_metrics()
        
        assert "uptime_seconds" in metrics
        assert metrics["uptime_seconds"] > 0
        assert metrics["uptime_seconds"] >= 0.1
    
    @pytest.mark.asyncio
    async def test_get_metrics_empty_state(self, metrics_service):
        """Test get_metrics returns correct structure when no requests recorded."""
        metrics = await metrics_service.get_metrics()
        
        assert "uptime_seconds" in metrics
        assert "endpoints" in metrics
        assert metrics["endpoints"] == {}
    
    @pytest.mark.asyncio
    async def test_reset_metrics(self, metrics_service):
        """Test that reset_metrics clears all data and resets uptime."""
        # Record some requests
        await metrics_service.record_request("/test", 1.0, success=True)
        await metrics_service.record_request("/test", 2.0, success=False)
        
        # Wait a bit to accumulate uptime
        await asyncio.sleep(0.1)
        
        # Get metrics before reset
        metrics_before = await metrics_service.get_metrics()
        assert len(metrics_before["endpoints"]) == 1
        uptime_before = metrics_before["uptime_seconds"]
        
        # Reset metrics
        await metrics_service.reset_metrics()
        
        # Get metrics after reset
        metrics_after = await metrics_service.get_metrics()
        
        assert metrics_after["endpoints"] == {}
        assert metrics_after["uptime_seconds"] < uptime_before
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_thread_safety(self, metrics_service):
        """Test that concurrent requests are handled safely with async lock."""
        # Create multiple concurrent requests to the same endpoint
        tasks = [
            metrics_service.record_request("/concurrent", 0.1, success=True)
            for _ in range(100)
        ]
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Verify all requests were recorded correctly
        metrics = await metrics_service.get_metrics()
        endpoint_metrics = metrics["endpoints"]["/concurrent"]
        
        assert endpoint_metrics["total_requests"] == 100
        assert endpoint_metrics["successful_requests"] == 100
        assert endpoint_metrics["failed_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_multiple_endpoints(self, metrics_service):
        """Test concurrent requests to multiple endpoints."""
        # Create concurrent requests to different endpoints
        tasks = []
        for i in range(10):
            for endpoint in ["/endpoint1", "/endpoint2", "/endpoint3"]:
                tasks.append(
                    metrics_service.record_request(endpoint, 0.1, success=True)
                )
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Verify all requests were recorded correctly
        metrics = await metrics_service.get_metrics()
        
        assert len(metrics["endpoints"]) == 3
        for endpoint in ["/endpoint1", "/endpoint2", "/endpoint3"]:
            assert metrics["endpoints"][endpoint]["total_requests"] == 10
    
    @pytest.mark.asyncio
    async def test_response_time_precision(self, metrics_service):
        """Test that response times are tracked with precision."""
        response_times = [0.123, 0.456, 0.789]
        
        for rt in response_times:
            await metrics_service.record_request("/precise", rt, success=True)
        
        metrics = await metrics_service.get_metrics()
        endpoint_metrics = metrics["endpoints"]["/precise"]
        
        expected_avg = sum(response_times) / len(response_times)
        assert endpoint_metrics["average_response_time"] == pytest.approx(expected_avg, rel=1e-6)
    
    @pytest.mark.asyncio
    async def test_zero_response_time(self, metrics_service):
        """Test handling of zero response time."""
        await metrics_service.record_request("/instant", 0.0, success=True)
        
        metrics = await metrics_service.get_metrics()
        endpoint_metrics = metrics["endpoints"]["/instant"]
        
        assert endpoint_metrics["average_response_time"] == 0.0
    
    @pytest.mark.asyncio
    async def test_large_response_time(self, metrics_service):
        """Test handling of large response times."""
        await metrics_service.record_request("/slow", 30.5, success=False)
        
        metrics = await metrics_service.get_metrics()
        endpoint_metrics = metrics["endpoints"]["/slow"]
        
        assert endpoint_metrics["average_response_time"] == 30.5
        assert endpoint_metrics["failed_requests"] == 1
