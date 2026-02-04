"""
Unit tests for Health Service

Tests the HealthMonitor class functionality including API health checks,
external API connectivity checks, and system resource monitoring.

Validates: Requirements 5.6, 5.7
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import TimeoutException, HTTPError

from app.services.health_service import HealthMonitor, HealthStatus
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.openrouter_api_key = "test-api-key"
    settings.openrouter_base_url = "https://openrouter.ai/api/v1"
    return settings


@pytest.fixture
def health_monitor(mock_settings):
    """Create HealthMonitor instance for testing."""
    return HealthMonitor(mock_settings)


@pytest.mark.asyncio
async def test_check_api_health(health_monitor):
    """Test that API health check returns healthy status."""
    result = await health_monitor._check_api_health()
    
    assert result["status"] == HealthStatus.HEALTHY
    assert "message" in result
    assert result["message"] == "API is running"


@pytest.mark.asyncio
async def test_check_external_api_success(health_monitor):
    """Test external API check when API is reachable and returns 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("app.services.health_service.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        result = await health_monitor._check_external_api()
        
        assert result["status"] == HealthStatus.HEALTHY
        assert "External API is reachable" in result["message"]


@pytest.mark.asyncio
async def test_check_external_api_degraded(health_monitor):
    """Test external API check when API returns non-200 status."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    
    with patch("app.services.health_service.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        result = await health_monitor._check_external_api()
        
        assert result["status"] == HealthStatus.DEGRADED
        assert "503" in result["message"]


@pytest.mark.asyncio
async def test_check_external_api_timeout(health_monitor):
    """Test external API check when request times out."""
    with patch("app.services.health_service.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=TimeoutException("Timeout")
        )
        
        result = await health_monitor._check_external_api()
        
        assert result["status"] == HealthStatus.UNHEALTHY
        assert "timeout" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_external_api_http_error(health_monitor):
    """Test external API check when HTTP error occurs."""
    with patch("app.services.health_service.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=HTTPError("Connection error")
        )
        
        result = await health_monitor._check_external_api()
        
        assert result["status"] == HealthStatus.UNHEALTHY
        assert "HTTP error" in result["message"]


@pytest.mark.asyncio
async def test_check_external_api_general_exception(health_monitor):
    """Test external API check when unexpected exception occurs."""
    with patch("app.services.health_service.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        result = await health_monitor._check_external_api()
        
        assert result["status"] == HealthStatus.UNHEALTHY
        assert "unreachable" in result["message"].lower()


@pytest.mark.asyncio
async def test_check_system_resources_healthy(health_monitor):
    """Test system resource check when resources are healthy."""
    with patch("app.services.health_service.psutil") as mock_psutil:
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_memory.available = 4 * 1024 * 1024 * 1024  # 4GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        result = await health_monitor._check_system_resources()
        
        assert result["status"] == HealthStatus.HEALTHY
        assert result["cpu_percent"] == 50.0
        assert result["memory_percent"] == 60.0
        assert result["memory_available_mb"] == 4096.0


@pytest.mark.asyncio
async def test_check_system_resources_degraded_cpu(health_monitor):
    """Test system resource check when CPU usage is high."""
    with patch("app.services.health_service.psutil") as mock_psutil:
        mock_psutil.cpu_percent.return_value = 95.0
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_memory.available = 4 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_memory
        
        result = await health_monitor._check_system_resources()
        
        assert result["status"] == HealthStatus.DEGRADED
        assert result["cpu_percent"] == 95.0


@pytest.mark.asyncio
async def test_check_system_resources_degraded_memory(health_monitor):
    """Test system resource check when memory usage is high."""
    with patch("app.services.health_service.psutil") as mock_psutil:
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = MagicMock()
        mock_memory.percent = 95.0
        mock_memory.available = 512 * 1024 * 1024  # 512MB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        result = await health_monitor._check_system_resources()
        
        assert result["status"] == HealthStatus.DEGRADED
        assert result["memory_percent"] == 95.0


@pytest.mark.asyncio
async def test_check_health_all_healthy(health_monitor):
    """Test comprehensive health check when all components are healthy."""
    with patch.object(health_monitor, "_check_api_health", new_callable=AsyncMock) as mock_api, \
         patch.object(health_monitor, "_check_external_api", new_callable=AsyncMock) as mock_ext, \
         patch.object(health_monitor, "_check_system_resources", new_callable=AsyncMock) as mock_sys:
        
        mock_api.return_value = {"status": HealthStatus.HEALTHY, "message": "OK"}
        mock_ext.return_value = {"status": HealthStatus.HEALTHY, "message": "OK"}
        mock_sys.return_value = {
            "status": HealthStatus.HEALTHY,
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "memory_available_mb": 4096.0
        }
        
        result = await health_monitor.check_health()
        
        assert result["status"] == HealthStatus.HEALTHY
        assert "checks" in result
        assert "api" in result["checks"]
        assert "external_api" in result["checks"]
        assert "system" in result["checks"]
        assert "timestamp" in result


@pytest.mark.asyncio
async def test_check_health_degraded(health_monitor):
    """Test comprehensive health check when one component is degraded."""
    with patch.object(health_monitor, "_check_api_health", new_callable=AsyncMock) as mock_api, \
         patch.object(health_monitor, "_check_external_api", new_callable=AsyncMock) as mock_ext, \
         patch.object(health_monitor, "_check_system_resources", new_callable=AsyncMock) as mock_sys:
        
        mock_api.return_value = {"status": HealthStatus.HEALTHY, "message": "OK"}
        mock_ext.return_value = {"status": HealthStatus.DEGRADED, "message": "Slow"}
        mock_sys.return_value = {
            "status": HealthStatus.HEALTHY,
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "memory_available_mb": 4096.0
        }
        
        result = await health_monitor.check_health()
        
        assert result["status"] == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_check_health_unhealthy(health_monitor):
    """Test comprehensive health check when one component is unhealthy."""
    with patch.object(health_monitor, "_check_api_health", new_callable=AsyncMock) as mock_api, \
         patch.object(health_monitor, "_check_external_api", new_callable=AsyncMock) as mock_ext, \
         patch.object(health_monitor, "_check_system_resources", new_callable=AsyncMock) as mock_sys:
        
        mock_api.return_value = {"status": HealthStatus.HEALTHY, "message": "OK"}
        mock_ext.return_value = {"status": HealthStatus.UNHEALTHY, "message": "Down"}
        mock_sys.return_value = {
            "status": HealthStatus.HEALTHY,
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "memory_available_mb": 4096.0
        }
        
        result = await health_monitor.check_health()
        
        assert result["status"] == HealthStatus.UNHEALTHY
