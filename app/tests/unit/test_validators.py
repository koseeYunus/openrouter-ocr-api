"""
Unit Tests for FileValidator

Tests file validation logic including type, size, and content validation.

Validates: Requirements 3.2, 4.3, 4.4
"""

import pytest
from fastapi import HTTPException, UploadFile
from io import BytesIO
from app.utils.validators import FileValidator
from app.config import Settings


@pytest.fixture
def settings():
    """Create test settings with validation parameters."""
    return Settings(
        openrouter_api_key="test-key",
        max_file_size_mb=10,
        allowed_image_types=["image/jpeg", "image/png", "image/webp"]
    )


@pytest.fixture
def validator(settings):
    """Create FileValidator instance for testing."""
    return FileValidator(settings)


def create_upload_file(
    content: bytes,
    filename: str = "test.jpg",
    content_type: str = "image/jpeg"
) -> UploadFile:
    """Helper function to create UploadFile for testing."""
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers={"content-type": content_type}
    )


@pytest.mark.asyncio
async def test_validate_valid_jpeg_file(validator, sample_image_bytes):
    """Test validation passes for valid JPEG file."""
    file = create_upload_file(
        sample_image_bytes,
        filename="test.jpg",
        content_type="image/jpeg"
    )
    
    result = await validator.validate_image_file(file)
    
    assert result == sample_image_bytes
    assert len(result) > 0


@pytest.mark.asyncio
async def test_validate_valid_png_file(validator, sample_image_bytes):
    """Test validation passes for valid PNG file."""
    file = create_upload_file(
        sample_image_bytes,
        filename="test.png",
        content_type="image/png"
    )
    
    result = await validator.validate_image_file(file)
    
    assert result == sample_image_bytes


@pytest.mark.asyncio
async def test_validate_valid_webp_file(validator, sample_image_bytes):
    """Test validation passes for valid WebP file."""
    file = create_upload_file(
        sample_image_bytes,
        filename="test.webp",
        content_type="image/webp"
    )
    
    result = await validator.validate_image_file(file)
    
    assert result == sample_image_bytes


@pytest.mark.asyncio
async def test_validate_invalid_content_type(validator, sample_image_bytes):
    """Test validation fails for invalid content type."""
    file = create_upload_file(
        sample_image_bytes,
        filename="test.pdf",
        content_type="application/pdf"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await validator.validate_image_file(file)
    
    assert exc_info.value.status_code == 400
    assert "Invalid file type" in exc_info.value.detail
    assert "application/pdf" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_empty_file(validator):
    """Test validation fails for empty file."""
    file = create_upload_file(
        b"",
        filename="empty.jpg",
        content_type="image/jpeg"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await validator.validate_image_file(file)
    
    assert exc_info.value.status_code == 400
    assert "Empty file" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_file_too_large(validator):
    """Test validation fails for file exceeding size limit."""
    # Create 11MB file (exceeds 10MB limit)
    large_content = b"x" * (11 * 1024 * 1024)
    file = create_upload_file(
        large_content,
        filename="large.jpg",
        content_type="image/jpeg"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await validator.validate_image_file(file)
    
    assert exc_info.value.status_code == 400
    assert "too large" in exc_info.value.detail.lower()
    assert "10MB" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_file_at_size_limit(validator):
    """Test validation passes for file exactly at size limit."""
    # Create exactly 10MB file
    content = b"x" * (10 * 1024 * 1024)
    file = create_upload_file(
        content,
        filename="limit.jpg",
        content_type="image/jpeg"
    )
    
    result = await validator.validate_image_file(file)
    
    assert result == content
    assert len(result) == 10 * 1024 * 1024


@pytest.mark.asyncio
async def test_validate_file_just_under_limit(validator):
    """Test validation passes for file just under size limit."""
    # Create 9.9MB file
    content = b"x" * int(9.9 * 1024 * 1024)
    file = create_upload_file(
        content,
        filename="under.jpg",
        content_type="image/jpeg"
    )
    
    result = await validator.validate_image_file(file)
    
    assert result == content


@pytest.mark.asyncio
async def test_validate_file_just_over_limit(validator):
    """Test validation fails for file just over size limit."""
    # Create 10.1MB file
    content = b"x" * int(10.1 * 1024 * 1024)
    file = create_upload_file(
        content,
        filename="over.jpg",
        content_type="image/jpeg"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await validator.validate_image_file(file)
    
    assert exc_info.value.status_code == 400
    assert "too large" in exc_info.value.detail.lower()


def test_validate_file_extension_valid(validator):
    """Test file extension validation for valid extensions."""
    assert validator.validate_file_extension("test.jpg") is True
    assert validator.validate_file_extension("test.jpeg") is True
    assert validator.validate_file_extension("test.png") is True
    assert validator.validate_file_extension("test.webp") is True
    assert validator.validate_file_extension("TEST.JPG") is True  # Case insensitive


def test_validate_file_extension_invalid(validator):
    """Test file extension validation for invalid extensions."""
    assert validator.validate_file_extension("test.pdf") is False
    assert validator.validate_file_extension("test.txt") is False
    assert validator.validate_file_extension("test.gif") is False
    assert validator.validate_file_extension("test") is False
    assert validator.validate_file_extension(None) is False
    assert validator.validate_file_extension("") is False


@pytest.mark.asyncio
async def test_validator_with_custom_settings():
    """Test validator respects custom settings."""
    custom_settings = Settings(
        openrouter_api_key="test-key",
        max_file_size_mb=5,  # Custom 5MB limit
        allowed_image_types=["image/jpeg"]  # Only JPEG allowed
    )
    custom_validator = FileValidator(custom_settings)
    
    # Test custom size limit
    content = b"x" * (6 * 1024 * 1024)  # 6MB
    file = create_upload_file(content, content_type="image/jpeg")
    
    with pytest.raises(HTTPException) as exc_info:
        await custom_validator.validate_image_file(file)
    
    assert exc_info.value.status_code == 400
    assert "5MB" in exc_info.value.detail
    
    # Test custom allowed types
    file_png = create_upload_file(b"test", content_type="image/png")
    
    with pytest.raises(HTTPException) as exc_info:
        await custom_validator.validate_image_file(file_png)
    
    assert exc_info.value.status_code == 400
    assert "image/png" in exc_info.value.detail


@pytest.mark.asyncio
async def test_error_messages_are_descriptive(validator):
    """Test that error messages provide helpful information."""
    # Test invalid type error message
    file = create_upload_file(b"test", content_type="application/pdf")
    
    with pytest.raises(HTTPException) as exc_info:
        await validator.validate_image_file(file)
    
    error_detail = exc_info.value.detail
    assert "Invalid file type" in error_detail
    assert "application/pdf" in error_detail
    assert "image/jpeg" in error_detail
    assert "image/png" in error_detail
    assert "image/webp" in error_detail
    
    # Test size error message
    large_file = create_upload_file(
        b"x" * (11 * 1024 * 1024),
        content_type="image/jpeg"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await validator.validate_image_file(large_file)
    
    error_detail = exc_info.value.detail
    assert "too large" in error_detail.lower()
    assert "MB" in error_detail
    assert "10" in error_detail  # Max size mentioned
