"""
Unit tests for OCR Service

Tests the OCRService class functionality including:
- Image encoding
- Prompt building
- Confidence calculation
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response, HTTPStatusError, TimeoutException
from app.services.ocr_service import OCRService
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        openrouter_api_key="test-api-key",
        openrouter_base_url="https://test.api.com",
        ocr_model_id="test-model",
        ocr_timeout_seconds=30
    )


@pytest.fixture
def ocr_service(mock_settings):
    """Create OCRService instance with mock settings."""
    return OCRService(mock_settings)


@pytest.mark.asyncio
async def test_encode_image(ocr_service):
    """Test image encoding to base64."""
    test_bytes = b"test image data"
    encoded = await ocr_service.encode_image(test_bytes)
    
    assert isinstance(encoded, str)
    assert len(encoded) > 0
    # Verify it's valid base64
    import base64
    decoded = base64.b64decode(encoded)
    assert decoded == test_bytes


def test_build_prompt_without_language(ocr_service):
    """Test prompt building without language parameter."""
    prompt = ocr_service._build_prompt(None)
    
    assert "transcribe the handwritten text" in prompt.lower()
    assert "return only the text found" in prompt.lower()
    assert "The text is in" not in prompt


def test_build_prompt_with_language(ocr_service):
    """Test prompt building with language parameter."""
    prompt = ocr_service._build_prompt("Turkish")
    
    assert "transcribe the handwritten text" in prompt.lower()
    assert "The text is in Turkish" in prompt
    assert "return only the text found" in prompt.lower()


def test_calculate_confidence_normal_text(ocr_service):
    """Test confidence calculation for normal text."""
    response_data = {
        "choices": [
            {
                "message": {"content": "This is a normal text"},
                "finish_reason": "stop"
            }
        ]
    }
    
    confidence = ocr_service._calculate_confidence(
        response_data, 
        "This is a normal text"
    )
    
    assert confidence == 0.95


def test_calculate_confidence_short_text(ocr_service):
    """Test confidence calculation for very short text."""
    response_data = {
        "choices": [
            {
                "message": {"content": "Hi"},
                "finish_reason": "stop"
            }
        ]
    }
    
    confidence = ocr_service._calculate_confidence(response_data, "Hi")
    
    assert confidence == 0.85


def test_calculate_confidence_incomplete_response(ocr_service):
    """Test confidence calculation when response is incomplete."""
    response_data = {
        "choices": [
            {
                "message": {"content": "Some text"},
                "finish_reason": "length"
            }
        ]
    }
    
    confidence = ocr_service._calculate_confidence(
        response_data, 
        "Some text"
    )
    
    assert confidence == 0.80


@pytest.mark.asyncio
async def test_process_handwriting_success(ocr_service):
    """Test successful OCR processing."""
    test_image = b"fake image data"
    mock_response_data = {
        "choices": [
            {
                "message": {"content": "Extracted handwritten text"},
                "finish_reason": "stop"
            }
        ]
    }
    
    # Mock the HTTP client
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()
    
    ocr_service.client.post = AsyncMock(return_value=mock_response)
    
    # Process handwriting
    text, confidence, processing_time, model_used = await ocr_service.process_handwriting(
        test_image
    )
    
    assert text == "Extracted handwritten text"
    assert 0.0 <= confidence <= 1.0
    assert processing_time >= 0.0
    assert model_used in ocr_service.settings.ocr_model_fallback_list
    
    # Verify API was called correctly
    ocr_service.client.post.assert_called_once()
    call_args = ocr_service.client.post.call_args
    assert call_args[0][0] == "/chat/completions"
    assert "json" in call_args[1]


@pytest.mark.asyncio
async def test_process_handwriting_with_language(ocr_service):
    """Test OCR processing with language parameter."""
    test_image = b"fake image data"
    mock_response_data = {
        "choices": [
            {
                "message": {"content": "Türkçe metin"},
                "finish_reason": "stop"
            }
        ]
    }
    
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()
    
    ocr_service.client.post = AsyncMock(return_value=mock_response)
    
    # Process with language
    text, confidence, processing_time, model_used = await ocr_service.process_handwriting(
        test_image,
        language="Turkish"
    )
    
    assert text == "Türkçe metin"
    assert model_used in ocr_service.settings.ocr_model_fallback_list
    
    # Verify language was included in prompt
    call_args = ocr_service.client.post.call_args
    payload = call_args[1]["json"]
    prompt = payload["messages"][0]["content"][0]["text"]
    assert "Turkish" in prompt


@pytest.mark.asyncio
async def test_process_handwriting_timeout(ocr_service):
    """Test OCR processing timeout handling with fallback."""
    test_image = b"fake image data"
    
    # Mock timeout exception for all models
    ocr_service.client.post = AsyncMock(
        side_effect=TimeoutException("Request timeout")
    )
    
    # Should raise Exception after all models fail
    with pytest.raises(Exception) as exc_info:
        await ocr_service.process_handwriting(test_image)
    
    assert "All OCR models failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_handwriting_http_error(ocr_service):
    """Test OCR processing HTTP error handling with fallback."""
    test_image = b"fake image data"
    
    # Mock HTTP error for all models
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = HTTPStatusError(
        "Server error",
        request=MagicMock(),
        response=mock_response
    )
    
    ocr_service.client.post = AsyncMock(return_value=mock_response)
    
    # Should raise Exception after all models fail
    with pytest.raises(Exception) as exc_info:
        await ocr_service.process_handwriting(test_image)
    
    assert "All OCR models failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_handwriting_unexpected_error(ocr_service):
    """Test OCR processing unexpected error handling."""
    test_image = b"fake image data"
    
    # Mock unexpected error
    ocr_service.client.post = AsyncMock(
        side_effect=Exception("Unexpected error")
    )
    
    # Should raise Exception
    with pytest.raises(Exception):
        await ocr_service.process_handwriting(test_image)


@pytest.mark.asyncio
async def test_process_handwriting_fallback_success(ocr_service):
    """Test that fallback mechanism works when first model fails."""
    test_image = b"fake image data"
    
    # First call fails with HTTP error, second succeeds
    mock_error_response = MagicMock(spec=Response)
    mock_error_response.status_code = 500
    mock_error_response.raise_for_status.side_effect = HTTPStatusError(
        "Server error",
        request=MagicMock(),
        response=mock_error_response
    )
    
    mock_success_response = MagicMock(spec=Response)
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {
        "choices": [
            {
                "message": {"content": "Fallback model success"},
                "finish_reason": "stop"
            }
        ]
    }
    mock_success_response.raise_for_status = MagicMock()
    
    # First call fails, second succeeds
    ocr_service.client.post = AsyncMock(
        side_effect=[mock_error_response, mock_success_response]
    )
    
    # Process handwriting
    text, confidence, processing_time, model_used = await ocr_service.process_handwriting(
        test_image
    )
    
    assert text == "Fallback model success"
    assert model_used == ocr_service.settings.ocr_model_fallback_list[1]
    
    # Verify API was called twice (first failed, second succeeded)
    assert ocr_service.client.post.call_count == 2


@pytest.mark.asyncio
async def test_close(ocr_service):
    """Test closing the OCR service."""
    ocr_service.client.aclose = AsyncMock()
    
    await ocr_service.close()
    
    ocr_service.client.aclose.assert_called_once()
