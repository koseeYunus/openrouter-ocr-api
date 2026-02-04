"""
Configuration Management Module

This module provides centralized configuration management using Pydantic Settings.
All configuration is loaded from environment variables with sensible defaults.

Validates: Requirements 6.1, 6.2, 6.3, 6.4
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All sensitive configuration (API keys) must be provided via environment variables.
    Optional parameters have sensible defaults for development and production use.
    """
    
    # API Configuration
    app_name: str = Field(
        default="Handwriting OCR Service",
        description="Application name displayed in API documentation"
    )
    app_version: str = Field(
        default="2.0.0",
        description="Application version"
    )
    environment: str = Field(
        default="development",
        description="Environment: development, staging, or production"
    )
    
    # OpenRouter Configuration (Required)
    openrouter_api_key: str = Field(
        ...,
        description="OpenRouter API key (required)"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    ocr_model_id: str = Field(
        default="qwen/qwen-2.5-vl-72b-instruct:free",
        description="OCR model identifier (deprecated - use ocr_model_fallback_list)"
    )
    ocr_model_fallback_list: list[str] = Field(
        default=[
            "google/gemini-2.0-flash-exp:free",
            "qwen/qwen2.5-vl-72b-instruct:free",
            "meta-llama/llama-3.2-11b-vision-instruct:free"
        ],
        description="Prioritized list of OCR models for fallback mechanism"
    )
    
    # Rate Limiting Configuration
    rate_limit_per_minute: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum requests per minute per IP address"
    )
    rate_limit_window: int = Field(
        default=60,
        ge=1,
        description="Rate limit window in seconds"
    )
    
    # File Upload Limits
    max_file_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum file size in megabytes"
    )
    allowed_image_types: list[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="Allowed image MIME types"
    )
    
    # Timeouts
    ocr_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="OCR processing timeout in seconds"
    )
    external_api_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="External API call timeout in seconds"
    )
    
    # CORS Configuration
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    log_file: Optional[str] = Field(
        default="logs/app.log",
        description="Log file path (None for console only)"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(
                f"log_level must be one of {allowed_levels}, got '{v}'"
            )
        return v_upper
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values."""
        allowed_envs = ["development", "staging", "production"]
        v_lower = v.lower()
        if v_lower not in allowed_envs:
            raise ValueError(
                f"environment must be one of {allowed_envs}, got '{v}'"
            )
        return v_lower
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    This function ensures only one Settings instance is created and reused
    throughout the application lifecycle.
    
    Returns:
        Settings: Application settings instance
        
    Raises:
        ValidationError: If required configuration is missing or invalid
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
