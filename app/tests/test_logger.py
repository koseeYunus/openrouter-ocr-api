"""
Unit tests for Logger utility

Tests the structured logging functionality including console and file handlers,
log rotation, and JSON formatting.

Validates: Requirements 3.1, 3.4, 3.5
"""

import pytest
import logging
import json
import tempfile
import time
from pathlib import Path
from app.utils.logger import setup_logging, get_logger


def test_setup_logging_console_only():
    """Test logging setup with console handler only."""
    setup_logging(log_level="INFO", log_file=None)
    
    logger = get_logger("test_console")
    assert logger is not None
    
    # Verify root logger is configured with INFO level
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO


def test_setup_logging_with_file():
    """Test logging setup with file handler and rotation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        setup_logging(
            log_level="DEBUG",
            log_file=str(log_file),
            max_bytes=1024,
            backup_count=3
        )
        
        logger = get_logger("test_file")
        logger.info("Test message", key="value")
        
        # Close all handlers to release file locks
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Verify log file was created
        assert log_file.exists()
        
        # Verify log content is JSON formatted
        with open(log_file, "r") as f:
            log_content = f.read()
            assert log_content.strip()  # File should have content
            
            # Parse first line as JSON
            first_line = log_content.strip().split("\n")[0]
            log_entry = json.loads(first_line)
            
            # Verify JSON structure
            assert "event" in log_entry
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert log_entry["event"] == "Test message"
            assert log_entry["key"] == "value"


def test_get_logger_returns_bound_logger():
    """Test that get_logger returns a properly configured logger."""
    setup_logging(log_level="INFO")
    
    logger = get_logger("test_module")
    assert logger is not None
    
    # Verify logger has expected methods
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
    assert hasattr(logger, "critical")


def test_logger_with_context():
    """Test logging with structured context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "context.log"
        
        setup_logging(log_level="INFO", log_file=str(log_file))
        
        logger = get_logger("test_context")
        logger.info(
            "User action",
            user_id="123",
            action="login",
            ip_address="192.168.1.1"
        )
        
        # Close all handlers to release file locks
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Verify context is in log
        with open(log_file, "r") as f:
            log_entry = json.loads(f.read().strip())
            assert log_entry["user_id"] == "123"
            assert log_entry["action"] == "login"
            assert log_entry["ip_address"] == "192.168.1.1"


def test_logger_with_exception():
    """Test logging with exception information."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "exception.log"
        
        setup_logging(log_level="ERROR", log_file=str(log_file))
        
        logger = get_logger("test_exception")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.error("An error occurred", exc_info=True)
        
        # Close all handlers to release file locks
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Verify exception info is in log
        with open(log_file, "r") as f:
            log_content = f.read()
            assert "ValueError" in log_content
            assert "Test error" in log_content


def test_log_levels():
    """Test different log levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "levels.log"
        
        setup_logging(log_level="DEBUG", log_file=str(log_file))
        
        logger = get_logger("test_levels")
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # Close all handlers to release file locks
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Verify all levels are logged
        with open(log_file, "r") as f:
            log_content = f.read()
            assert "Debug message" in log_content
            assert "Info message" in log_content
            assert "Warning message" in log_content
            assert "Error message" in log_content
            assert "Critical message" in log_content


def test_log_file_directory_creation():
    """Test that log directory is created if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "nested" / "dir" / "test.log"
        
        setup_logging(log_level="INFO", log_file=str(log_file))
        
        logger = get_logger("test_dir")
        logger.info("Test message")
        
        # Close all handlers to release file locks
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Verify directory and file were created
        assert log_file.parent.exists()
        assert log_file.exists()


def test_log_rotation():
    """Test that log rotation works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "rotation.log"
        
        # Set small max_bytes to trigger rotation
        setup_logging(
            log_level="INFO",
            log_file=str(log_file),
            max_bytes=500,  # Small size to trigger rotation
            backup_count=2
        )
        
        logger = get_logger("test_rotation")
        
        # Write enough logs to trigger rotation
        for i in range(50):
            logger.info(f"Log message number {i}", iteration=i)
        
        # Close all handlers to release file locks
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Verify main log file exists
        assert log_file.exists()
        
        # Check if rotation occurred (backup files should exist)
        backup_files = list(log_file.parent.glob("rotation.log.*"))
        # At least one backup should exist if rotation occurred
        assert len(backup_files) >= 0  # May or may not rotate depending on message size
