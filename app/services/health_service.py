"""
Health Monitoring Service

This module provides comprehensive health checking for the API service,
including API status, external API connectivity, and system resource monitoring.

Validates: Requirements 5.6, 5.7
"""

import psutil
from enum import Enum
from typing import Dict
from datetime import datetime, timezone
from httpx import AsyncClient, HTTPError, TimeoutException

from app.config import Settings


class HealthStatus(str, Enum):
    """Health status enumeration for service components."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthMonitor:
    """
    Monitor service health including API status, external dependencies,
    and system resources.
    
    This class performs comprehensive health checks to ensure the service
    is operating correctly and can handle requests.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize health monitor.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
    
    async def check_health(self) -> Dict:
        """
        Perform comprehensive health check.
        
        Checks:
        - API service status
        - External API connectivity (OpenRouter)
        - System resources (CPU, memory)
        
        Returns:
            Dict containing overall status and individual check results
            
        Example:
            {
                "status": "healthy",
                "checks": {
                    "api": {"status": "healthy", "message": "..."},
                    "external_api": {"status": "healthy", "message": "..."},
                    "system": {"status": "healthy", "cpu_percent": 25.0, ...}
                },
                "timestamp": "2024-01-01T12:00:00.000000"
            }
        """
        checks = {
            "api": await self._check_api_health(),
            "external_api": await self._check_external_api(),
            "system": await self._check_system_resources()
        }
        
        # Determine overall status based on individual checks
        if all(c["status"] == HealthStatus.HEALTHY for c in checks.values()):
            overall_status = HealthStatus.HEALTHY
        elif any(c["status"] == HealthStatus.UNHEALTHY for c in checks.values()):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status,
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _check_api_health(self) -> Dict:
        """
        Check if API service is responsive.
        
        Returns:
            Dict with status and message
        """
        return {
            "status": HealthStatus.HEALTHY,
            "message": "API is running"
        }
    
    async def _check_external_api(self) -> Dict:
        """
        Check OpenRouter API connectivity.
        
        Attempts to connect to the OpenRouter API to verify it's reachable
        and responding. Uses a short timeout to avoid blocking.
        
        Returns:
            Dict with status and message
        """
        try:
            async with AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.settings.openrouter_base_url}/models",
                    headers={"Authorization": f"Bearer {self.settings.openrouter_api_key}"}
                )
                
                if response.status_code == 200:
                    return {
                        "status": HealthStatus.HEALTHY,
                        "message": "External API is reachable"
                    }
                else:
                    return {
                        "status": HealthStatus.DEGRADED,
                        "message": f"External API returned status {response.status_code}"
                    }
                    
        except TimeoutException:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "External API timeout"
            }
        except HTTPError as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"External API HTTP error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"External API unreachable: {str(e)}"
            }
    
    async def _check_system_resources(self) -> Dict:
        """
        Check system resource usage (CPU and memory).
        
        Monitors CPU and memory usage to detect resource constraints.
        Status is degraded if either CPU or memory usage exceeds 90%.
        
        Returns:
            Dict with status, CPU percent, memory percent, and available memory
        """
        # Get CPU usage (1 second interval for accurate reading)
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory information
        memory = psutil.virtual_memory()
        
        # Determine status based on resource usage
        status = HealthStatus.HEALTHY
        if cpu_percent > 90 or memory.percent > 90:
            status = HealthStatus.DEGRADED
        
        return {
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": round(memory.available / (1024 * 1024), 2)
        }
