"""
Logger Utility Module

This module provides structured logging using structlog with console and file handlers,
log rotation, and JSON formatting.

Validates: Requirements 3.1, 3.4, 3.5
"""

import structlog
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Configure structured logging with console and file handlers.
    
    Sets up structlog with JSON formatting, log rotation, and both console
    and file output. Logs include timestamp, level, logger name, and context.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for console only)
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup log files to keep (default: 5)
    
    Example:
        >>> setup_logging(log_level="INFO", log_file="logs/app.log")
        >>> logger = get_logger("my_module")
        >>> logger.info("Application started", version="2.0.0")
    
    Validates: Requirements 3.1, 3.4, 3.5
    """
    # Create handlers list
    handlers: list[logging.Handler] = []
    
    # Always add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    handlers.append(console_handler)
    
    # Add file handler with rotation if log_file is specified
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, log_level))
        handlers.append(file_handler)
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level),
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Configure structlog processors
    structlog.configure(
        processors=[
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add log level
            structlog.stdlib.add_log_level,
            # Format positional arguments
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add timestamp in ISO format
            structlog.processors.TimeStamper(fmt="iso"),
            # Render stack info if available
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Decode unicode
            structlog.processors.UnicodeDecoder(),
            # Render as JSON
            structlog.processors.JSONRenderer()
        ],
        # Use dict for context
        context_class=dict,
        # Use standard library logger factory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger on first use
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured structured logger.
    
    Returns a structlog logger bound to the specified name. The logger
    supports structured logging with automatic JSON formatting and context.
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        BoundLogger: Configured structlog logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", request_id="123", user_id="456")
        >>> logger.error("Failed to process", error="Connection timeout", exc_info=True)
    
    Note:
        Call setup_logging() before using get_logger() to ensure proper configuration.
    """
    return structlog.get_logger(name)
