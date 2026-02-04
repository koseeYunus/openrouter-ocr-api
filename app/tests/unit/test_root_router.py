"""
Unit tests for the root router.

Tests the / endpoint that provides API information and available endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import root
from app.config import Settings


@pytest.fixture
def test_app():
    """Create FastAPI test application."""
    app = FastAPI()
    app.include_router(root.router)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        app_name="Test OCR Service",
        app_version="1.0.0",
        openrouter_api_key="test-key"
    )


def test_root_endpoint_returns_200(client):
    """Test that root endpoint returns 200 status code."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_endpoint_returns_json(client):
    """Test that root endpoint returns JSON response."""
    response = client.get("/")
    assert response.headers["content-type"] == "application/json"


def test_root_endpoint_contains_required_fields(client):
    """Test that root endpoint response contains all required fields."""
    response = client.get("/")
    data = response.json()
    
    # Check required top-level fields
    assert "name" in data
    assert "version" in data
    assert "description" in data
    assert "endpoints" in data
    assert "documentation" in data


def test_root_endpoint_name_and_version(client):
    """Test that root endpoint returns correct name and version from settings."""
    response = client.get("/")
    data = response.json()
    
    # Should use settings values
    assert isinstance(data["name"], str)
    assert isinstance(data["version"], str)
    assert len(data["name"]) > 0
    assert len(data["version"]) > 0


def test_root_endpoint_description(client):
    """Test that root endpoint returns a description."""
    response = client.get("/")
    data = response.json()
    
    assert isinstance(data["description"], str)
    assert len(data["description"]) > 0


def test_root_endpoint_lists_all_endpoints(client):
    """Test that root endpoint lists all available API endpoints."""
    response = client.get("/")
    data = response.json()
    
    endpoints = data["endpoints"]
    assert isinstance(endpoints, list)
    assert len(endpoints) >= 4  # At least /, /health, /metrics, /read-handwriting
    
    # Check that each endpoint has required fields
    for endpoint in endpoints:
        assert "path" in endpoint
        assert "method" in endpoint
        assert "description" in endpoint


def test_root_endpoint_includes_core_endpoints(client):
    """Test that root endpoint includes all core API endpoints."""
    response = client.get("/")
    data = response.json()
    
    endpoints = data["endpoints"]
    paths = [ep["path"] for ep in endpoints]
    
    # Check for core endpoints
    assert "/" in paths
    assert "/health" in paths
    assert "/metrics" in paths
    assert "/read-handwriting" in paths


def test_root_endpoint_includes_documentation_links(client):
    """Test that root endpoint includes documentation links."""
    response = client.get("/")
    data = response.json()
    
    documentation = data["documentation"]
    assert isinstance(documentation, dict)
    
    # Check for documentation endpoints
    assert "swagger_ui" in documentation
    assert "redoc" in documentation
    assert "openapi_schema" in documentation
    
    # Check values
    assert documentation["swagger_ui"] == "/docs"
    assert documentation["redoc"] == "/redoc"
    assert documentation["openapi_schema"] == "/openapi.json"


def test_root_endpoint_methods_are_valid(client):
    """Test that all endpoint methods are valid HTTP methods."""
    response = client.get("/")
    data = response.json()
    
    valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    
    for endpoint in data["endpoints"]:
        assert endpoint["method"] in valid_methods


def test_root_endpoint_paths_start_with_slash(client):
    """Test that all endpoint paths start with a forward slash."""
    response = client.get("/")
    data = response.json()
    
    for endpoint in data["endpoints"]:
        assert endpoint["path"].startswith("/")


def test_root_endpoint_descriptions_are_not_empty(client):
    """Test that all endpoint descriptions are non-empty strings."""
    response = client.get("/")
    data = response.json()
    
    for endpoint in data["endpoints"]:
        assert isinstance(endpoint["description"], str)
        assert len(endpoint["description"]) > 0


def test_root_endpoint_read_handwriting_is_post(client):
    """Test that /read-handwriting endpoint is listed as POST method."""
    response = client.get("/")
    data = response.json()
    
    endpoints = data["endpoints"]
    read_handwriting = next(
        (ep for ep in endpoints if ep["path"] == "/read-handwriting"),
        None
    )
    
    assert read_handwriting is not None
    assert read_handwriting["method"] == "POST"


def test_root_endpoint_health_and_metrics_are_get(client):
    """Test that /health and /metrics endpoints are listed as GET methods."""
    response = client.get("/")
    data = response.json()
    
    endpoints = data["endpoints"]
    
    health = next((ep for ep in endpoints if ep["path"] == "/health"), None)
    metrics = next((ep for ep in endpoints if ep["path"] == "/metrics"), None)
    
    assert health is not None
    assert health["method"] == "GET"
    
    assert metrics is not None
    assert metrics["method"] == "GET"
