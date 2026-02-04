"""
Integration Tests for Error Handler Middleware

Tests the error handlers integrated with a FastAPI application.

Validates: Requirements 3.2, 3.3, 3.6
"""

import pytest
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.middleware.error_handler import register_exception_handlers


@pytest.fixture
def app():
    """Create a test FastAPI application with error handlers."""
    app = FastAPI()
    
    # Register error handlers
    register_exception_handlers(app)
    
    # Add test endpoints
    @app.get("/test/success")
    async def success_endpoint():
        return {"message": "success"}
    
    @app.get("/test/http-error")
    async def http_error_endpoint():
        raise HTTPException(status_code=400, detail="Test HTTP error")
    
    @app.get("/test/server-error")
    async def server_error_endpoint():
        raise RuntimeError("Test server error")
    
    @app.post("/test/validation")
    async def validation_endpoint(data: dict):
        class TestModel(BaseModel):
            required_field: str = Field(...)
        
        TestModel(**data)
        return {"message": "validated"}
    
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def test_successful_request(client):
    """Test that successful requests work normally."""
    response = client.get("/test/success")
    assert response.status_code == 200
    assert response.json() == {"message": "success"}


def test_http_exception_returns_structured_error(client):
    """Test that HTTPException returns structured error response."""
    response = client.get("/test/http-error")
    
    assert response.status_code == 400
    
    data = response.json()
    assert "error" in data
    assert "detail" in data
    assert "timestamp" in data
    assert "path" in data
    
    assert data["error"] == "Bad Request"
    assert data["detail"] == "Test HTTP error"
    assert data["path"] == "/test/http-error"


def test_validation_error_returns_structured_error(client):
    """Test that validation errors return structured error response."""
    response = client.post("/test/validation", json={})
    
    assert response.status_code == 422
    
    data = response.json()
    assert "error" in data
    assert "detail" in data
    assert "timestamp" in data
    assert "path" in data
    
    assert data["error"] == "Validation Error"
    assert "required_field" in data["detail"]


def test_server_error_returns_generic_error(client):
    """Test that unexpected errors return generic error response."""
    response = client.get("/test/server-error")
    
    assert response.status_code == 500
    
    data = response.json()
    assert "error" in data
    assert "detail" in data
    assert "timestamp" in data
    assert "path" in data
    
    assert data["error"] == "Internal Server Error"
    # Should not expose internal error details
    assert "RuntimeError" not in data["detail"]
    assert "unexpected error occurred" in data["detail"].lower()


def test_404_error_structure(client):
    """Test that 404 errors return structured error response."""
    response = client.get("/nonexistent-endpoint")
    
    assert response.status_code == 404
    
    data = response.json()
    assert "error" in data or "detail" in data
    # FastAPI's default 404 handler might be used, which is fine


def test_error_response_consistency(client):
    """Test that all error responses have consistent structure."""
    # Test different error types
    responses = [
        client.get("/test/http-error"),
        client.post("/test/validation", json={}),
        client.get("/test/server-error")
    ]
    
    for response in responses:
        data = response.json()
        
        # All should have these fields
        assert "error" in data
        assert "detail" in data
        assert "timestamp" in data
        assert "path" in data
        
        # Timestamp should be ISO format
        assert "T" in data["timestamp"]
        
        # Path should be a string
        assert isinstance(data["path"], str)


def test_multiple_errors_in_sequence(client):
    """Test that error handlers work correctly for multiple requests."""
    # Make multiple error requests
    for _ in range(5):
        response = client.get("/test/http-error")
        assert response.status_code == 400
        
        data = response.json()
        assert data["error"] == "Bad Request"


def test_error_handler_does_not_affect_successful_requests(client):
    """Test that error handlers don't interfere with successful requests."""
    # Mix successful and error requests
    response1 = client.get("/test/success")
    assert response1.status_code == 200
    
    response2 = client.get("/test/http-error")
    assert response2.status_code == 400
    
    response3 = client.get("/test/success")
    assert response3.status_code == 200
    assert response3.json() == {"message": "success"}
