"""
Unit Tests for Error Handler Middleware

Tests the global exception handlers for HTTPException, ValidationError,
and general exceptions.

Validates: Requirements 3.2, 3.3, 3.6
"""

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError, BaseModel, Field
from datetime import datetime, UTC
import json

from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    register_exception_handlers
)
from app.models.responses import ErrorResponse


class MockRequest:
    """Mock request object for testing."""
    
    def __init__(self, path: str = "/test", method: str = "GET"):
        self.url = type('obj', (object,), {'path': path})()
        self.method = method
        self.client = type('obj', (object,), {'host': '127.0.0.1'})()


@pytest.mark.asyncio
async def test_http_exception_handler_400():
    """Test HTTP exception handler with 400 Bad Request."""
    request = MockRequest(path="/read-handwriting")
    exc = HTTPException(status_code=400, detail="Invalid file type")
    
    response = await http_exception_handler(request, exc)
    
    assert response.status_code == 400
    
    content = json.loads(response.body.decode())
    assert content["error"] == "Bad Request"
    assert content["detail"] == "Invalid file type"
    assert content["path"] == "/read-handwriting"
    assert "timestamp" in content


@pytest.mark.asyncio
async def test_http_exception_handler_404():
    """Test HTTP exception handler with 404 Not Found."""
    request = MockRequest(path="/nonexistent")
    exc = HTTPException(status_code=404, detail="Resource not found")
    
    response = await http_exception_handler(request, exc)
    
    assert response.status_code == 404
    
    content = json.loads(response.body.decode())
    assert content["error"] == "Not Found"
    assert content["detail"] == "Resource not found"


@pytest.mark.asyncio
async def test_http_exception_handler_429():
    """Test HTTP exception handler with 429 Too Many Requests."""
    request = MockRequest(path="/read-handwriting")
    exc = HTTPException(status_code=429, detail="Rate limit exceeded")
    
    response = await http_exception_handler(request, exc)
    
    assert response.status_code == 429
    
    content = json.loads(response.body.decode())
    assert content["error"] == "Too Many Requests"
    assert content["detail"] == "Rate limit exceeded"


@pytest.mark.asyncio
async def test_http_exception_handler_502():
    """Test HTTP exception handler with 502 Bad Gateway."""
    request = MockRequest(path="/read-handwriting")
    exc = HTTPException(status_code=502, detail="External API unavailable")
    
    response = await http_exception_handler(request, exc)
    
    assert response.status_code == 502
    
    content = json.loads(response.body.decode())
    assert content["error"] == "Bad Gateway"
    assert content["detail"] == "External API unavailable"


@pytest.mark.asyncio
async def test_http_exception_handler_504():
    """Test HTTP exception handler with 504 Gateway Timeout."""
    request = MockRequest(path="/read-handwriting")
    exc = HTTPException(status_code=504, detail="Request timeout")
    
    response = await http_exception_handler(request, exc)
    
    assert response.status_code == 504
    
    content = json.loads(response.body.decode())
    assert content["error"] == "Gateway Timeout"
    assert content["detail"] == "Request timeout"


@pytest.mark.asyncio
async def test_validation_exception_handler():
    """Test validation exception handler."""
    request = MockRequest(path="/read-handwriting")
    
    # Create a mock validation error
    class TestModel(BaseModel):
        required_field: str = Field(...)
    
    try:
        TestModel.model_validate({})
    except ValidationError as exc:
        response = await validation_exception_handler(request, exc)
        
        assert response.status_code == 422
        
        content = json.loads(response.body.decode())
        assert content["error"] == "Validation Error"
        assert "required_field" in content["detail"]
        assert content["path"] == "/read-handwriting"
        assert "timestamp" in content


@pytest.mark.asyncio
async def test_general_exception_handler():
    """Test general exception handler for unexpected errors."""
    request = MockRequest(path="/read-handwriting")
    exc = RuntimeError("Unexpected error occurred")
    
    response = await general_exception_handler(request, exc)
    
    assert response.status_code == 500
    
    content = json.loads(response.body.decode())
    assert content["error"] == "Internal Server Error"
    assert "unexpected error occurred" in content["detail"].lower()
    assert content["path"] == "/read-handwriting"
    assert "timestamp" in content


@pytest.mark.asyncio
async def test_general_exception_handler_with_different_exceptions():
    """Test general exception handler with various exception types."""
    request = MockRequest(path="/test")
    
    # Test with ValueError
    exc = ValueError("Invalid value")
    response = await general_exception_handler(request, exc)
    assert response.status_code == 500
    
    # Test with KeyError
    exc = KeyError("missing_key")
    response = await general_exception_handler(request, exc)
    assert response.status_code == 500
    
    # Test with AttributeError
    exc = AttributeError("object has no attribute")
    response = await general_exception_handler(request, exc)
    assert response.status_code == 500


def test_register_exception_handlers():
    """Test registering exception handlers with FastAPI app."""
    app = FastAPI()
    
    # Should not raise any exceptions
    register_exception_handlers(app)
    
    # Verify handlers are registered
    assert len(app.exception_handlers) > 0


@pytest.mark.asyncio
async def test_error_response_structure():
    """Test that all error responses follow the ErrorResponse model structure."""
    request = MockRequest(path="/test")
    
    # Test HTTP exception
    exc = HTTPException(status_code=400, detail="Test error")
    response = await http_exception_handler(request, exc)
    content = json.loads(response.body.decode())
    
    # Validate against ErrorResponse model
    error_response = ErrorResponse(**content)
    assert error_response.error == "Bad Request"
    assert error_response.detail == "Test error"
    assert error_response.path == "/test"
    
    # Verify timestamp is valid ISO format
    datetime.fromisoformat(error_response.timestamp)


@pytest.mark.asyncio
async def test_error_handler_includes_request_context():
    """Test that error handlers include request context in responses."""
    request = MockRequest(path="/api/v1/endpoint", method="POST")
    exc = HTTPException(status_code=400, detail="Bad request")
    
    response = await http_exception_handler(request, exc)
    content = json.loads(response.body.decode())
    
    # Verify path is included
    assert content["path"] == "/api/v1/endpoint"
    
    # Verify timestamp is recent (within last minute)
    timestamp = datetime.fromisoformat(content["timestamp"])
    now = datetime.now(UTC)
    time_diff = (now - timestamp).total_seconds()
    assert time_diff < 60  # Should be within last minute


@pytest.mark.asyncio
async def test_error_response_json_serializable():
    """Test that all error responses are JSON serializable."""
    request = MockRequest(path="/test")
    
    # Test various exception types
    exceptions = [
        HTTPException(status_code=400, detail="Bad request"),
        RuntimeError("Runtime error"),
    ]
    
    for exc in exceptions:
        if isinstance(exc, HTTPException):
            response = await http_exception_handler(request, exc)
        else:
            response = await general_exception_handler(request, exc)
        
        # Should be able to parse JSON without errors
        content = json.loads(response.body.decode())
        assert isinstance(content, dict)
        assert "error" in content
        assert "detail" in content
        assert "timestamp" in content
        assert "path" in content
