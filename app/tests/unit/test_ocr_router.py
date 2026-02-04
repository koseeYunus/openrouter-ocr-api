"""
Unit Tests for OCR Router

This module tests the OCR router endpoint including file validation,
OCR processing, metrics collection, and error handling.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from io import BytesIO

from app.routers import ocr
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Settings(
        openrouter_api_key="test-key",
        max_file_size_mb=10,
        allowed_image_types=["image/jpeg", "image/png", "image/webp"],
        ocr_timeout_seconds=30,
        ocr_model_id="test-model"
    )
    return settings


@pytest.fixture
def app(mock_settings):
    """Create FastAPI test application."""
    test_app = FastAPI()
    test_app.include_router(ocr.router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_image_file():
    """Create a valid test image file."""
    # Create a small test image (1KB)
    image_data = b"fake_image_data" * 100
    return BytesIO(image_data)


@pytest.fixture
def large_image_file():
    """Create a large test image file (>10MB)."""
    # Create a file larger than 10MB
    image_data = b"x" * (11 * 1024 * 1024)
    return BytesIO(image_data)


class TestOCRRouter:
    """Test cases for OCR router."""
    
    def test_ocr_endpoint_exists(self, client):
        """Test that the OCR endpoint exists."""
        # Try to access the endpoint (will fail without proper setup, but endpoint should exist)
        response = client.post("/read-handwriting")
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
    
    @patch('app.routers.ocr.get_ocr_service')
    @patch('app.routers.ocr.get_file_validator')
    @patch('app.routers.ocr.get_metrics_service')
    def test_successful_ocr_processing(
        self,
        mock_get_metrics,
        mock_get_validator,
        mock_get_ocr,
        client,
        valid_image_file,
        mock_settings
    ):
        """Test successful OCR processing."""
        # Setup mocks
        mock_ocr_service = AsyncMock()
        mock_ocr_service.process_handwriting.return_value = (
            "Extracted text",
            0.95,
            2.34,
            "google/gemini-2.0-flash-exp:free"
        )
        mock_get_ocr.return_value = mock_ocr_service
        
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.return_value = b"fake_image_data"
        mock_get_validator.return_value = mock_validator
        
        mock_metrics = AsyncMock()
        mock_metrics.record_request = AsyncMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Make request
        files = {"file": ("test.jpg", valid_image_file, "image/jpeg")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "confidence" in data
        assert "processing_time" in data
        assert "model_used" in data
    
    @patch('app.routers.ocr.get_file_validator')
    def test_invalid_file_type(self, mock_get_validator, client):
        """Test rejection of invalid file type."""
        from fastapi import HTTPException
        
        # Setup mock to raise validation error
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.side_effect = HTTPException(
            status_code=400,
            detail="Invalid file type"
        )
        mock_get_validator.return_value = mock_validator
        
        # Make request with invalid file
        files = {"file": ("test.txt", BytesIO(b"text"), "text/plain")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify error response
        assert response.status_code == 400
    
    @patch('app.routers.ocr.get_file_validator')
    def test_file_too_large(self, mock_get_validator, client, large_image_file):
        """Test rejection of files that are too large."""
        from fastapi import HTTPException
        
        # Setup mock to raise validation error
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.side_effect = HTTPException(
            status_code=400,
            detail="File too large"
        )
        mock_get_validator.return_value = mock_validator
        
        # Make request with large file
        files = {"file": ("large.jpg", large_image_file, "image/jpeg")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify error response
        assert response.status_code == 400
    
    @patch('app.routers.ocr.get_file_validator')
    def test_empty_file(self, mock_get_validator, client):
        """Test rejection of empty files."""
        from fastapi import HTTPException
        
        # Setup mock to raise validation error
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.side_effect = HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )
        mock_get_validator.return_value = mock_validator
        
        # Make request with empty file
        files = {"file": ("empty.jpg", BytesIO(b""), "image/jpeg")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify error response
        assert response.status_code == 400
    
    @patch('app.routers.ocr.get_ocr_service')
    @patch('app.routers.ocr.get_file_validator')
    @patch('app.routers.ocr.get_metrics_service')
    def test_ocr_with_language_parameter(
        self,
        mock_get_metrics,
        mock_get_validator,
        mock_get_ocr,
        client,
        valid_image_file
    ):
        """Test OCR processing with language parameter."""
        # Setup mocks
        mock_ocr_service = AsyncMock()
        mock_ocr_service.process_handwriting.return_value = (
            "Türkçe metin",
            0.95,
            2.34,
            "qwen/qwen2.5-vl-72b-instruct:free"
        )
        mock_get_ocr.return_value = mock_ocr_service
        
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.return_value = b"fake_image_data"
        mock_get_validator.return_value = mock_validator
        
        mock_metrics = AsyncMock()
        mock_metrics.record_request = AsyncMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Make request with language parameter
        files = {"file": ("test.jpg", valid_image_file, "image/jpeg")}
        data = {"language": "Turkish"}
        response = client.post("/read-handwriting", files=files, data=data)
        
        # Verify response
        assert response.status_code == 200
        result = response.json()
        assert result["language"] == "Turkish"
    
    @patch('app.routers.ocr.get_ocr_service')
    @patch('app.routers.ocr.get_file_validator')
    @patch('app.routers.ocr.get_metrics_service')
    def test_ocr_timeout_error(
        self,
        mock_get_metrics,
        mock_get_validator,
        mock_get_ocr,
        client,
        valid_image_file
    ):
        """Test OCR timeout handling."""
        # Setup mocks
        mock_ocr_service = AsyncMock()
        mock_ocr_service.process_handwriting.side_effect = TimeoutError("OCR timeout")
        mock_get_ocr.return_value = mock_ocr_service
        
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.return_value = b"fake_image_data"
        mock_get_validator.return_value = mock_validator
        
        mock_metrics = AsyncMock()
        mock_metrics.record_request = AsyncMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Make request
        files = {"file": ("test.jpg", valid_image_file, "image/jpeg")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify timeout error response
        assert response.status_code == 504
    
    @patch('app.routers.ocr.get_ocr_service')
    @patch('app.routers.ocr.get_file_validator')
    @patch('app.routers.ocr.get_metrics_service')
    def test_external_api_error(
        self,
        mock_get_metrics,
        mock_get_validator,
        mock_get_ocr,
        client,
        valid_image_file
    ):
        """Test external API error handling."""
        # Setup mocks
        mock_ocr_service = AsyncMock()
        mock_ocr_service.process_handwriting.side_effect = Exception("API error")
        mock_get_ocr.return_value = mock_ocr_service
        
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.return_value = b"fake_image_data"
        mock_get_validator.return_value = mock_validator
        
        mock_metrics = AsyncMock()
        mock_metrics.record_request = AsyncMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Make request
        files = {"file": ("test.jpg", valid_image_file, "image/jpeg")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify error response (502 for external API errors)
        assert response.status_code == 502
    
    @patch('app.routers.ocr.get_ocr_service')
    @patch('app.routers.ocr.get_file_validator')
    @patch('app.routers.ocr.get_metrics_service')
    def test_metrics_recorded_on_success(
        self,
        mock_get_metrics,
        mock_get_validator,
        mock_get_ocr,
        client,
        valid_image_file
    ):
        """Test that metrics are recorded on successful request."""
        # Setup mocks
        mock_ocr_service = AsyncMock()
        mock_ocr_service.process_handwriting.return_value = (
            "Extracted text",
            0.95,
            2.34,
            "google/gemini-2.0-flash-exp:free"
        )
        mock_get_ocr.return_value = mock_ocr_service
        
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.return_value = b"fake_image_data"
        mock_get_validator.return_value = mock_validator
        
        mock_metrics = AsyncMock()
        mock_metrics.record_request = AsyncMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Make request
        files = {"file": ("test.jpg", valid_image_file, "image/jpeg")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify metrics were recorded
        assert response.status_code == 200
        mock_metrics.record_request.assert_called_once()
        call_args = mock_metrics.record_request.call_args
        assert call_args[1]["endpoint"] == "/read-handwriting"
        assert call_args[1]["success"] is True
    
    @patch('app.routers.ocr.get_file_validator')
    @patch('app.routers.ocr.get_metrics_service')
    def test_metrics_recorded_on_failure(
        self,
        mock_get_metrics,
        mock_get_validator,
        client
    ):
        """Test that metrics are recorded on failed request."""
        from fastapi import HTTPException
        
        # Setup mocks
        mock_validator = AsyncMock()
        mock_validator.validate_image_file.side_effect = HTTPException(
            status_code=400,
            detail="Invalid file"
        )
        mock_get_validator.return_value = mock_validator
        
        mock_metrics = AsyncMock()
        mock_metrics.record_request = AsyncMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Make request
        files = {"file": ("test.txt", BytesIO(b"text"), "text/plain")}
        response = client.post("/read-handwriting", files=files)
        
        # Verify error response and metrics
        assert response.status_code == 400
        # Metrics should be recorded even on failure
        mock_metrics.record_request.assert_called_once()
        call_args = mock_metrics.record_request.call_args
        assert call_args[1]["endpoint"] == "/read-handwriting"
        assert call_args[1]["success"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
