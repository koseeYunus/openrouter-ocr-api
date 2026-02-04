"""
Pytest Configuration and Shared Fixtures

This module contains shared test fixtures and pytest configuration
for all test modules.
"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient
from fastapi import FastAPI


@pytest.fixture
def app() -> FastAPI:
    """
    Create a FastAPI application instance for testing.
    
    This fixture will be updated once the application factory is implemented.
    """
    # Placeholder - will be implemented in later tasks
    from fastapi import FastAPI
    app = FastAPI()
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing API endpoints.
    
    Yields:
        AsyncClient: Configured async HTTP client
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_image_bytes() -> bytes:
    """
    Provide sample image bytes for testing.
    
    Returns:
        bytes: Sample image data
    """
    # Simple 1x1 pixel PNG image
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


@pytest.fixture
def large_file_bytes() -> bytes:
    """
    Provide a large file (>10MB) for testing file size validation.
    
    Returns:
        bytes: Large file data
    """
    return b"x" * (11 * 1024 * 1024)  # 11MB


@pytest.fixture
def mock_ocr_response() -> dict:
    """
    Provide a mock OCR API response for testing.
    
    Returns:
        dict: Mock OpenRouter API response
    """
    return {
        "choices": [
            {
                "message": {
                    "content": "Sample extracted text from handwriting"
                }
            }
        ]
    }
