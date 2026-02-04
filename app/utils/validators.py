"""
Input Validation Module

This module provides validation utilities for file uploads and other inputs.
Ensures security and data integrity through comprehensive validation.

Validates: Requirements 3.2, 4.3, 4.4
"""

from fastapi import UploadFile, HTTPException
from app.config import Settings
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class FileValidator:
    """
    Validator for uploaded files with comprehensive security checks.
    
    This validator ensures that uploaded files meet size, type, and content
    requirements before processing. It provides descriptive error messages
    to help users understand validation failures.
    
    Attributes:
        settings: Application settings containing validation parameters
        max_size_bytes: Maximum allowed file size in bytes
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize FileValidator with application settings.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.max_size_bytes = settings.max_file_size_bytes
        logger.info(
            "FileValidator initialized",
            max_size_mb=settings.max_file_size_mb,
            allowed_types=settings.allowed_image_types
        )
    
    async def validate_image_file(self, file: UploadFile) -> bytes:
        """
        Validate uploaded image file for type, size, and content.
        
        This method performs comprehensive validation:
        1. Checks if file content type is allowed
        2. Reads file contents
        3. Validates file is not empty
        4. Validates file size is within limits
        
        Args:
            file: Uploaded file from FastAPI request
            
        Returns:
            bytes: File contents if validation passes
            
        Raises:
            HTTPException: If validation fails with descriptive error message
                - 400 Bad Request: Invalid file type, size, or empty file
        
        Example:
            >>> validator = FileValidator(settings)
            >>> file_bytes = await validator.validate_image_file(uploaded_file)
        """
        # Validate content type
        if file.content_type not in self.settings.allowed_image_types:
            error_msg = (
                f"Invalid file type '{file.content_type}'. "
                f"Allowed types: {', '.join(self.settings.allowed_image_types)}"
            )
            logger.warning(
                "File validation failed: invalid content type",
                content_type=file.content_type,
                filename=file.filename
            )
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Read file contents
        try:
            contents = await file.read()
        except Exception as e:
            error_msg = f"Failed to read file: {str(e)}"
            logger.error(
                "File validation failed: read error",
                error=str(e),
                filename=file.filename
            )
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Validate file is not empty
        if len(contents) == 0:
            error_msg = "Empty file uploaded. Please upload a valid image file."
            logger.warning(
                "File validation failed: empty file",
                filename=file.filename
            )
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Validate file size
        file_size_mb = len(contents) / (1024 * 1024)
        if len(contents) > self.max_size_bytes:
            error_msg = (
                f"File too large ({file_size_mb:.2f}MB). "
                f"Maximum allowed size: {self.settings.max_file_size_mb}MB"
            )
            logger.warning(
                "File validation failed: file too large",
                file_size_mb=file_size_mb,
                max_size_mb=self.settings.max_file_size_mb,
                filename=file.filename
            )
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        logger.info(
            "File validation successful",
            filename=file.filename,
            content_type=file.content_type,
            size_mb=file_size_mb
        )
        
        return contents
    
    def validate_file_extension(self, filename: Optional[str]) -> bool:
        """
        Validate file extension matches allowed image types.
        
        This is an additional security check beyond MIME type validation.
        
        Args:
            filename: Name of the uploaded file
            
        Returns:
            bool: True if extension is valid, False otherwise
        """
        if not filename:
            return False
        
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        return f'.{file_ext}' in allowed_extensions
