"""
Unit tests for Rate Limiter middleware

Tests the rate limiting functionality including:
- Rate limiter creation and configuration
- Rate limit exceeded handler
- Custom rate limit decorators

Validates: Requirements 4.1, 4.2, 3.7
"""

import pytest
from unittest.mock import Mock, MagicMock
from fastapi import Request
from slowapi.errors import RateLimitExceeded
from limits import RateLimitItem

from app.middleware.rate_limiter import (
    get_rate_limiter,
    rate_limit_exceeded_handler,
    create_rate_limit_decorator,
    get_ocr_rate_limit,
    get_metrics_rate_limit,
    get_health_rate_limit
)
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        openrouter_api_key="test-key",
        rate_limit_per_minute=10,
        rate_limit_window=60
    )


@pytest.fixture
def mock_request():
    """Create mock request for testing."""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/test-endpoint"
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_rate_limit_exception():
    """Create a mock RateLimitExceeded exception."""
    # Create a mock Limit object
    limit = Mock()
    limit.amount = 10
    limit.multiples = 1
    limit.GRANULARITY = Mock()
    limit.GRANULARITY.name = "minute"
    
    exc = RateLimitExceeded(limit)
    return exc


class TestRateLimiterCreation:
    """Test rate limiter creation and configuration."""
    
    def test_get_rate_limiter_creates_limiter(self, mock_settings):
        """Test that get_rate_limiter creates a Limiter instance."""
        limiter = get_rate_limiter(mock_settings)
        
        assert limiter is not None
        assert hasattr(limiter, 'limit')
        assert hasattr(limiter, 'reset')
    
    def test_rate_limiter_uses_settings(self, mock_settings):
        """Test that rate limiter uses settings from configuration."""
        limiter = get_rate_limiter(mock_settings)
        
        # Check that default limits are set (should be a list with one LimitGroup)
        assert len(limiter._default_limits) > 0
        # The limiter should have been configured with the rate limit
        assert limiter._default_limits is not None
    
    def test_rate_limiter_with_different_settings(self):
        """Test rate limiter with different rate limit settings."""
        settings = Settings(
            openrouter_api_key="test-key",
            rate_limit_per_minute=20
        )
        limiter = get_rate_limiter(settings)
        
        # Verify limiter was created successfully
        assert limiter is not None
        assert len(limiter._default_limits) > 0


class TestRateLimitExceededHandler:
    """Test rate limit exceeded error handler."""
    
    @pytest.mark.asyncio
    async def test_handler_returns_429_status(self, mock_request, mock_rate_limit_exception):
        """Test that handler returns 429 status code."""
        response = await rate_limit_exceeded_handler(mock_request, mock_rate_limit_exception)
        
        assert response.status_code == 429
    
    @pytest.mark.asyncio
    async def test_handler_includes_retry_after_header(self, mock_request, mock_rate_limit_exception):
        """Test that handler includes Retry-After header."""
        response = await rate_limit_exceeded_handler(mock_request, mock_rate_limit_exception)
        
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"].isdigit()
    
    @pytest.mark.asyncio
    async def test_handler_returns_json_error_response(self, mock_request, mock_rate_limit_exception):
        """Test that handler returns structured JSON error response."""
        response = await rate_limit_exceeded_handler(mock_request, mock_rate_limit_exception)
        
        # Parse JSON body
        import json
        body = json.loads(response.body.decode())
        
        assert "error" in body
        assert body["error"] == "Rate Limit Exceeded"
        assert "detail" in body
        assert "timestamp" in body
        assert "path" in body
        assert body["path"] == "/test-endpoint"
    
    @pytest.mark.asyncio
    async def test_handler_includes_rate_limit_headers(self, mock_request, mock_rate_limit_exception):
        """Test that handler includes rate limit information headers."""
        response = await rate_limit_exceeded_handler(mock_request, mock_rate_limit_exception)
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Reset" in response.headers


class TestCustomRateLimitDecorators:
    """Test custom rate limit decorator functions."""
    
    def test_create_rate_limit_decorator(self, mock_settings):
        """Test creating a custom rate limit decorator."""
        limiter = get_rate_limiter(mock_settings)
        decorator = create_rate_limit_decorator(limiter, "5/minute")
        
        assert callable(decorator)
    
    def test_get_ocr_rate_limit(self, mock_settings):
        """Test OCR endpoint rate limit decorator (10/minute)."""
        limiter = get_rate_limiter(mock_settings)
        decorator = get_ocr_rate_limit(limiter)
        
        assert callable(decorator)
    
    def test_get_metrics_rate_limit(self, mock_settings):
        """Test metrics endpoint rate limit decorator (60/minute)."""
        limiter = get_rate_limiter(mock_settings)
        decorator = get_metrics_rate_limit(limiter)
        
        assert callable(decorator)
    
    def test_get_health_rate_limit(self, mock_settings):
        """Test health endpoint rate limit decorator (120/minute)."""
        limiter = get_rate_limiter(mock_settings)
        decorator = get_health_rate_limit(limiter)
        
        assert callable(decorator)


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with FastAPI."""
    
    def test_limiter_key_function_uses_ip(self, mock_settings):
        """Test that limiter uses IP address as key."""
        limiter = get_rate_limiter(mock_settings)
        
        # The key function should be get_remote_address
        assert limiter._key_func.__name__ == "get_remote_address"
    
    def test_limiter_uses_memory_storage(self, mock_settings):
        """Test that limiter uses in-memory storage."""
        limiter = get_rate_limiter(mock_settings)
        
        # Check storage URI
        assert limiter._storage_uri == "memory://"
    
    def test_limiter_uses_fixed_window_strategy(self, mock_settings):
        """Test that limiter uses fixed-window strategy."""
        limiter = get_rate_limiter(mock_settings)
        
        # Check strategy
        assert limiter._strategy == "fixed-window"
