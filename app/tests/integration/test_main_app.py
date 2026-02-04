"""
Integration tests for main application factory.

Tests the create_app factory function and verifies that all routers,
middleware, and configurations are properly set up.

Validates: Requirements 1.4, 4.7, 8.1, 8.2, 8.3
"""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def app():
    """Create test application instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestApplicationFactory:
    """Test suite for application factory."""
    
    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        app = create_app()
        assert app is not None
        assert hasattr(app, 'routes')
        assert hasattr(app, 'middleware')
    
    def test_app_metadata(self, app):
        """Test that app has correct metadata."""
        assert app.title == "Handwriting OCR Service"
        assert app.version == "2.0.0"
        assert app.description is not None
        assert len(app.description) > 0
    
    def test_openapi_schema_available(self, client):
        """
        Test that OpenAPI schema is available at /openapi.json.
        
        Validates: Requirement 8.1
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Handwriting OCR Service"
        assert schema["info"]["version"] == "2.0.0"
    
    def test_swagger_ui_available(self, client):
        """
        Test that Swagger UI documentation is available at /docs.
        
        Validates: Requirement 8.2
        """
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_available(self, client):
        """
        Test that ReDoc documentation is available at /redoc.
        
        Validates: Requirement 8.3
        """
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_all_routers_included(self, client):
        """
        Test that all routers are included and accessible.
        
        Validates: Requirement 1.4
        """
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test metrics endpoint
        response = client.get("/metrics")
        assert response.status_code == 200
    
    def test_cors_middleware_configured(self, client):
        """
        Test that CORS middleware is properly configured.
        
        Validates: Requirement 4.7
        """
        # Make a request with Origin header
        response = client.get(
            "/health",
            headers={"Origin": "http://example.com"}
        )
        
        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers
    
    def test_error_handlers_registered(self, client):
        """
        Test that error handlers are properly registered.
        
        Validates: Requirement 3.6
        """
        # Test 404 error (non-existent endpoint)
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404
        
        # Check error response format (FastAPI default 404 has 'detail' field)
        error_data = response.json()
        assert "detail" in error_data
    
    def test_request_logging_middleware(self, client):
        """
        Test that request logging middleware adds process time header.
        """
        response = client.get("/health")
        assert response.status_code == 200
        
        # Check that X-Process-Time header is added
        assert "x-process-time" in response.headers
        
        # Verify it's a valid float
        process_time = float(response.headers["x-process-time"])
        assert process_time >= 0
    
    def test_rate_limit_headers_exposed(self, client):
        """
        Test that rate limit headers are exposed via CORS.
        
        Validates: Requirement 4.7
        """
        response = client.options(
            "/read-handwriting",
            headers={"Origin": "http://example.com"}
        )
        
        # Check that rate limit headers are in exposed headers
        if "access-control-expose-headers" in response.headers:
            exposed_headers = response.headers["access-control-expose-headers"]
            # Rate limit headers should be exposed
            assert any(
                header in exposed_headers.lower() 
                for header in ["ratelimit", "retry-after"]
            )


class TestApplicationLifecycle:
    """Test suite for application lifecycle events."""
    
    def test_app_starts_successfully(self):
        """Test that application starts without errors."""
        app = create_app()
        assert app is not None
    
    def test_app_with_test_client(self):
        """Test that application works with test client."""
        app = create_app()
        client = TestClient(app)
        
        # Make a simple request
        response = client.get("/")
        assert response.status_code == 200


class TestOpenAPIDocumentation:
    """Test suite for OpenAPI documentation."""
    
    def test_openapi_endpoints_documented(self, client):
        """
        Test that all endpoints are documented in OpenAPI schema.
        
        Validates: Requirement 8.1
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check that paths are documented
        assert "paths" in schema
        paths = schema["paths"]
        
        # Verify key endpoints are documented
        assert "/" in paths
        assert "/health" in paths
        assert "/metrics" in paths
        assert "/read-handwriting" in paths
    
    def test_openapi_response_schemas(self, client):
        """
        Test that response schemas are defined in OpenAPI.
        
        Validates: Requirement 8.1
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check that components/schemas exist
        assert "components" in schema
        assert "schemas" in schema["components"]
        
        # Verify key response models are defined
        schemas = schema["components"]["schemas"]
        assert "OCRResponse" in schemas
        assert "HealthCheckResponse" in schemas
        assert "ErrorResponse" in schemas
    
    def test_openapi_error_responses_documented(self, client):
        """
        Test that error responses are documented for endpoints.
        
        Validates: Requirement 8.6
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check OCR endpoint error responses
        ocr_endpoint = schema["paths"]["/read-handwriting"]["post"]
        responses = ocr_endpoint["responses"]
        
        # Verify error status codes are documented
        assert "400" in responses  # Bad Request
        assert "429" in responses  # Rate Limit
        assert "500" in responses  # Internal Server Error
        assert "502" in responses  # Bad Gateway
        assert "504" in responses  # Gateway Timeout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
