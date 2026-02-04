"""
Integration tests for the root router.

Tests the / endpoint in a more realistic application context.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import root
from app.config import get_settings


@pytest.fixture
def app():
    """Create FastAPI app with root router for testing."""
    app = FastAPI(
        title="Test Handwriting OCR Service",
        version="2.0.0"
    )
    app.include_router(root.router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_root_endpoint_integration(client):
    """
    Integration test for root endpoint.
    
    Validates: Requirements 1.3
    """
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "name" in data
    assert "version" in data
    assert "description" in data
    assert "endpoints" in data
    assert "documentation" in data
    
    # Verify content
    assert isinstance(data["name"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["description"], str)
    assert isinstance(data["endpoints"], list)
    assert isinstance(data["documentation"], dict)


def test_root_endpoint_uses_settings(client):
    """Test that root endpoint uses actual application settings."""
    settings = get_settings()
    response = client.get("/")
    data = response.json()
    
    # Should match settings
    assert data["name"] == settings.app_name
    assert data["version"] == settings.app_version


def test_root_endpoint_api_discovery(client):
    """
    Test that root endpoint enables API discovery.
    
    A client should be able to discover all available endpoints
    and their documentation from the root endpoint.
    """
    response = client.get("/")
    data = response.json()
    
    # Should list all main endpoints
    endpoint_paths = [ep["path"] for ep in data["endpoints"]]
    
    assert "/" in endpoint_paths
    assert "/health" in endpoint_paths
    assert "/metrics" in endpoint_paths
    assert "/read-handwriting" in endpoint_paths
    
    # Should provide documentation links
    docs = data["documentation"]
    assert docs["swagger_ui"] == "/docs"
    assert docs["redoc"] == "/redoc"
    assert docs["openapi_schema"] == "/openapi.json"


def test_root_endpoint_response_format(client):
    """Test that root endpoint returns properly formatted JSON."""
    response = client.get("/")
    
    # Should be valid JSON
    assert response.headers["content-type"] == "application/json"
    
    # Should be parseable
    data = response.json()
    assert data is not None


def test_root_endpoint_endpoint_details(client):
    """Test that each endpoint in the list has complete details."""
    response = client.get("/")
    data = response.json()
    
    for endpoint in data["endpoints"]:
        # Each endpoint should have all required fields
        assert "path" in endpoint
        assert "method" in endpoint
        assert "description" in endpoint
        
        # Fields should be non-empty
        assert len(endpoint["path"]) > 0
        assert len(endpoint["method"]) > 0
        assert len(endpoint["description"]) > 0
        
        # Path should be valid
        assert endpoint["path"].startswith("/")
        
        # Method should be uppercase
        assert endpoint["method"].isupper()


def test_root_endpoint_consistency(client):
    """Test that root endpoint returns consistent results across multiple calls."""
    response1 = client.get("/")
    response2 = client.get("/")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Should return identical data
    assert data1 == data2


def test_root_endpoint_no_authentication_required(client):
    """Test that root endpoint is publicly accessible without authentication."""
    # Should work without any headers or authentication
    response = client.get("/")
    assert response.status_code == 200


def test_root_endpoint_cors_friendly(client):
    """Test that root endpoint can be called from browsers (CORS-friendly)."""
    # Simulate a browser request
    response = client.get(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "User-Agent": "Mozilla/5.0"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
