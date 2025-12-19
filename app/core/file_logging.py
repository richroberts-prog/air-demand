"""File logging configuration with rotation for persistent log storage.

This module provides file-based logging with automatic rotation:
- Size-based rotation to prevent disk fill
- Multiple backup files for history
- JSON format consistent with console logs
- Creates log directory if it doesn't exist
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import get_settings


def setup_file_logging() -> None:
    """Configure file logging with rotation.

    Creates a rotating file handler that:
    - Writes logs to configurable file path (default: logs/air.log)
    - Rotates when file reaches max size (default: 10MB)
    - Keeps N backup files (default: 5)
    - Uses JSON format matching console output

    The log directory is created if it doesn't exist.
    File logging can be disabled via LOG_FILE_ENABLED=false.
    """
    settings = get_settings()

    # Skip if file logging is disabled
    if not settings.log_file_enabled:
        return

    # Create log directory if it doesn't exist
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create rotating file handler
    file_handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=settings.log_file_max_bytes,
        backupCount=settings.log_file_backup_count,
        encoding="utf-8",
    )

    # Set formatter to match structlog's JSON output
    # We use the root logger to capture structlog's output
    file_handler.setLevel(logging.INFO)

    # Add handler to root logger (structlog outputs to root logger)
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
