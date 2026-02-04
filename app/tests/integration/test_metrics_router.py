"""
Integration tests for Metrics Router

Tests the /metrics endpoint integration with MetricsService.

Validates: Requirements 1.2, 5.5
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.routers.metrics import router


@pytest.fixture
def mock_metrics_service():
    """Create a mock MetricsService."""
    return MagicMock()


@pytest.fixture
def app(mock_metrics_service):
    """Create FastAPI app with metrics router for testing."""
    from app.routers import metrics
    
    # Override the dependency
    def override_get_metrics_service():
        return mock_metrics_service
    
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[metrics.get_metrics_service] = override_get_metrics_service
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_metrics_endpoint_success(client, mock_metrics_service):
    """Test /metrics endpoint returns metrics successfully."""
    # Configure mock
    mock_metrics_service.get_metrics = AsyncMock(return_value={
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
    })
    
    response = client.get("/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "uptime_seconds" in data
    assert "endpoints" in data
    assert data["uptime_seconds"] == 3600.0
    assert "/read-handwriting" in data["endpoints"]
    assert "/health" in data["endpoints"]


def test_metrics_endpoint_empty_metrics(client, mock_metrics_service):
    """Test /metrics endpoint returns empty metrics when no requests have been made."""
    mock_metrics_service.get_metrics = AsyncMock(return_value={
        "uptime_seconds": 10.0,
        "endpoints": {}
    })
    
    response = client.get("/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["uptime_seconds"] == 10.0
    assert data["endpoints"] == {}


def test_metrics_endpoint_response_structure(client, mock_metrics_service):
    """Test /metrics endpoint returns correct response structure."""
    mock_metrics_service.get_metrics = AsyncMock(return_value={
        "uptime_seconds": 1800.0,
        "endpoints": {
            "/read-handwriting": {
                "total_requests": 50,
                "successful_requests": 48,
                "failed_requests": 2,
                "average_response_time": 1.8,
                "error_rate": 0.04
            }
        }
    })
    
    response = client.get("/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure matches MetricsResponse model
    assert "uptime_seconds" in data
    assert "endpoints" in data
    assert isinstance(data["uptime_seconds"], float)
    assert isinstance(data["endpoints"], dict)
    
    # Verify endpoint metrics structure
    endpoint_metrics = data["endpoints"]["/read-handwriting"]
    assert "total_requests" in endpoint_metrics
    assert "successful_requests" in endpoint_metrics
    assert "failed_requests" in endpoint_metrics
    assert "average_response_time" in endpoint_metrics
    assert "error_rate" in endpoint_metrics
    
    # Verify metric values
    assert endpoint_metrics["total_requests"] == 50
    assert endpoint_metrics["successful_requests"] == 48
    assert endpoint_metrics["failed_requests"] == 2
    assert endpoint_metrics["average_response_time"] == 1.8
    assert endpoint_metrics["error_rate"] == 0.04


def test_metrics_endpoint_multiple_endpoints(client, mock_metrics_service):
    """Test /metrics endpoint tracks multiple endpoints correctly."""
    mock_metrics_service.get_metrics = AsyncMock(return_value={
        "uptime_seconds": 7200.0,
        "endpoints": {
            "/read-handwriting": {
                "total_requests": 200,
                "successful_requests": 190,
                "failed_requests": 10,
                "average_response_time": 2.3,
                "error_rate": 0.05
            },
            "/health": {
                "total_requests": 100,
                "successful_requests": 100,
                "failed_requests": 0,
                "average_response_time": 0.03,
                "error_rate": 0.0
            },
            "/metrics": {
                "total_requests": 20,
                "successful_requests": 20,
                "failed_requests": 0,
                "average_response_time": 0.02,
                "error_rate": 0.0
            }
        }
    })
    
    response = client.get("/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["endpoints"]) == 3
    assert "/read-handwriting" in data["endpoints"]
    assert "/health" in data["endpoints"]
    assert "/metrics" in data["endpoints"]


def test_metrics_endpoint_high_error_rate(client, mock_metrics_service):
    """Test /metrics endpoint correctly reports high error rates."""
    mock_metrics_service.get_metrics = AsyncMock(return_value={
        "uptime_seconds": 600.0,
        "endpoints": {
            "/read-handwriting": {
                "total_requests": 100,
                "successful_requests": 50,
                "failed_requests": 50,
                "average_response_time": 3.0,
                "error_rate": 0.5
            }
        }
    })
    
    response = client.get("/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    endpoint_metrics = data["endpoints"]["/read-handwriting"]
    assert endpoint_metrics["error_rate"] == 0.5
    assert endpoint_metrics["failed_requests"] == 50
    assert endpoint_metrics["successful_requests"] == 50
