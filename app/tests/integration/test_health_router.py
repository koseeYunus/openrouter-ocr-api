"""
Integration tests for Health Router

Tests the /health endpoint integration with HealthMonitor service.

Validates: Requirements 1.1, 5.6, 5.7
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.routers.health import router
from app.services.health_service import HealthStatus


@pytest.fixture
def app():
    """Create FastAPI app with health router for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_health_endpoint_success(client):
    """Test /health endpoint returns successful health check."""
    with patch("app.routers.health.HealthMonitor") as mock_monitor_class:
        # Mock the health monitor instance
        mock_monitor = MagicMock()
        mock_monitor.check_health = AsyncMock(return_value={
            "status": HealthStatus.HEALTHY,
            "checks": {
                "api": {"status": HealthStatus.HEALTHY, "message": "API is running"},
                "external_api": {"status": HealthStatus.HEALTHY, "message": "External API is reachable"},
                "system": {
                    "status": HealthStatus.HEALTHY,
                    "cpu_percent": 25.5,
                    "memory_percent": 45.2,
                    "memory_available_mb": 2048.5
                }
            },
            "timestamp": "2024-01-01T12:00:00.000000"
        })
        mock_monitor_class.return_value = mock_monitor
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == HealthStatus.HEALTHY
        assert "checks" in data
        assert "api" in data["checks"]
        assert "external_api" in data["checks"]
        assert "system" in data["checks"]
        assert "timestamp" in data


def test_health_endpoint_degraded(client):
    """Test /health endpoint returns degraded status when system is degraded."""
    with patch("app.routers.health.HealthMonitor") as mock_monitor_class:
        mock_monitor = MagicMock()
        mock_monitor.check_health = AsyncMock(return_value={
            "status": HealthStatus.DEGRADED,
            "checks": {
                "api": {"status": HealthStatus.HEALTHY, "message": "API is running"},
                "external_api": {"status": HealthStatus.DEGRADED, "message": "External API returned status 503"},
                "system": {
                    "status": HealthStatus.HEALTHY,
                    "cpu_percent": 50.0,
                    "memory_percent": 60.0,
                    "memory_available_mb": 1024.0
                }
            },
            "timestamp": "2024-01-01T12:00:00.000000"
        })
        mock_monitor_class.return_value = mock_monitor
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == HealthStatus.DEGRADED
        assert data["checks"]["external_api"]["status"] == HealthStatus.DEGRADED


def test_health_endpoint_unhealthy(client):
    """Test /health endpoint returns unhealthy status when external API is down."""
    with patch("app.routers.health.HealthMonitor") as mock_monitor_class:
        mock_monitor = MagicMock()
        mock_monitor.check_health = AsyncMock(return_value={
            "status": HealthStatus.UNHEALTHY,
            "checks": {
                "api": {"status": HealthStatus.HEALTHY, "message": "API is running"},
                "external_api": {"status": HealthStatus.UNHEALTHY, "message": "External API unreachable"},
                "system": {
                    "status": HealthStatus.HEALTHY,
                    "cpu_percent": 30.0,
                    "memory_percent": 40.0,
                    "memory_available_mb": 3072.0
                }
            },
            "timestamp": "2024-01-01T12:00:00.000000"
        })
        mock_monitor_class.return_value = mock_monitor
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == HealthStatus.UNHEALTHY
        assert data["checks"]["external_api"]["status"] == HealthStatus.UNHEALTHY


def test_health_endpoint_response_structure(client):
    """Test /health endpoint returns correct response structure."""
    with patch("app.routers.health.HealthMonitor") as mock_monitor_class:
        mock_monitor = MagicMock()
        mock_monitor.check_health = AsyncMock(return_value={
            "status": HealthStatus.HEALTHY,
            "checks": {
                "api": {"status": HealthStatus.HEALTHY, "message": "API is running"},
                "external_api": {"status": HealthStatus.HEALTHY, "message": "External API is reachable"},
                "system": {
                    "status": HealthStatus.HEALTHY,
                    "cpu_percent": 25.5,
                    "memory_percent": 45.2,
                    "memory_available_mb": 2048.5
                }
            },
            "timestamp": "2024-01-01T12:00:00.000000"
        })
        mock_monitor_class.return_value = mock_monitor
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure matches HealthCheckResponse model
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data
        
        # Verify checks structure
        assert isinstance(data["checks"], dict)
        assert "api" in data["checks"]
        assert "external_api" in data["checks"]
        assert "system" in data["checks"]
        
        # Verify system check includes resource metrics
        system_check = data["checks"]["system"]
        assert "cpu_percent" in system_check
        assert "memory_percent" in system_check
        assert "memory_available_mb" in system_check
