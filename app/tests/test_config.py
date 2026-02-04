"""
Unit tests for Configuration Manager

Tests the Settings class and configuration validation.
"""

import pytest
from pydantic import ValidationError
from app.config import Settings, get_settings
import os


class TestSettingsDefaults:
    """Test default values for optional configuration parameters."""
    
    def test_default_values_with_required_key(self, monkeypatch):
        """Test that default values are provided for optional parameters."""
        # Set only required environment variable
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        settings = Settings()
        
        # Verify defaults
        assert settings.app_name == "Handwriting OCR Service"
        assert settings.app_version == "2.0.0"
        assert settings.environment == "development"
        assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
        assert settings.ocr_model_id == "qwen/qwen2.5-vl-72b-instruct:free"
        assert settings.rate_limit_per_minute == 10
        assert settings.rate_limit_window == 60
        assert settings.max_file_size_mb == 10
        assert settings.allowed_image_types == ["image/jpeg", "image/png", "image/webp"]
        assert settings.ocr_timeout_seconds == 30
        assert settings.external_api_timeout == 30
        assert settings.cors_origins == ["*"]
        assert settings.log_level == "INFO"
        assert settings.log_file == "logs/app.log"
    
    def test_custom_values_override_defaults(self, monkeypatch):
        """Test that environment variables override default values."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        monkeypatch.setenv("APP_NAME", "Custom OCR Service")
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "20")
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "15")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        
        settings = Settings()
        
        assert settings.app_name == "Custom OCR Service"
        assert settings.rate_limit_per_minute == 20
        assert settings.max_file_size_mb == 15
        assert settings.log_level == "DEBUG"


class TestSettingsValidation:
    """Test configuration validation rules."""
    
    def test_missing_required_api_key_raises_error(self, monkeypatch, tmp_path):
        """Test that missing required API key raises ValidationError."""
        # Remove API key if it exists
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        
        # Create a temporary empty .env file to prevent loading from actual .env
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        # Verify error mentions the missing field
        error_str = str(exc_info.value)
        assert "openrouter_api_key" in error_str.lower()
    
    def test_invalid_log_level_raises_error(self, monkeypatch):
        """Test that invalid log level raises ValidationError."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_str = str(exc_info.value)
        assert "log_level" in error_str.lower()
    
    def test_valid_log_levels_accepted(self, monkeypatch):
        """Test that all valid log levels are accepted."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            monkeypatch.setenv("LOG_LEVEL", level)
            settings = Settings()
            assert settings.log_level == level
    
    def test_log_level_case_insensitive(self, monkeypatch):
        """Test that log level validation is case-insensitive."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        monkeypatch.setenv("LOG_LEVEL", "debug")
        
        settings = Settings()
        assert settings.log_level == "DEBUG"
    
    def test_invalid_environment_raises_error(self, monkeypatch):
        """Test that invalid environment raises ValidationError."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        monkeypatch.setenv("ENVIRONMENT", "invalid")
        
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_str = str(exc_info.value)
        assert "environment" in error_str.lower()
    
    def test_valid_environments_accepted(self, monkeypatch):
        """Test that all valid environments are accepted."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        valid_envs = ["development", "staging", "production"]
        for env in valid_envs:
            monkeypatch.setenv("ENVIRONMENT", env)
            settings = Settings()
            assert settings.environment == env
    
    def test_rate_limit_validation(self, monkeypatch):
        """Test rate limit value constraints."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        # Test minimum value
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
        settings = Settings()
        assert settings.rate_limit_per_minute == 1
        
        # Test maximum value
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")
        settings = Settings()
        assert settings.rate_limit_per_minute == 1000
        
        # Test invalid value (too low)
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
        with pytest.raises(ValidationError):
            Settings()
        
        # Test invalid value (too high)
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1001")
        with pytest.raises(ValidationError):
            Settings()


class TestSettingsProperties:
    """Test computed properties of Settings class."""
    
    def test_max_file_size_bytes_property(self, monkeypatch):
        """Test max_file_size_bytes property calculation."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        monkeypatch.setenv("MAX_FILE_SIZE_MB", "10")
        
        settings = Settings()
        assert settings.max_file_size_bytes == 10 * 1024 * 1024
    
    def test_is_production_property(self, monkeypatch):
        """Test is_production property."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.is_production is True
        assert settings.is_development is False
        
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings.is_production is False
        assert settings.is_development is True


class TestGetSettings:
    """Test get_settings singleton function."""
    
    def test_get_settings_returns_singleton(self, monkeypatch):
        """Test that get_settings returns the same instance."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        # Reset singleton
        import app.config
        app.config._settings = None
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_get_settings_with_valid_config(self, monkeypatch):
        """Test get_settings with valid configuration."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        # Reset singleton
        import app.config
        app.config._settings = None
        
        settings = get_settings()
        assert settings.openrouter_api_key == "test-key-123"
        assert settings.app_name == "Handwriting OCR Service"
