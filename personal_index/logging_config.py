"""
Logging configuration for personal-index.

Sets up structured logging with file and console handlers.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    verbose: bool = False,
) -> logging.Logger:
    """Set up logging for personal-index.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses default location.
        verbose: If True, use DEBUG level.

    Returns:
        Configured logger instance.
    """
    if verbose:
        level = "DEBUG"

    logger = logging.getLogger("personal_index")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler
    if log_file is None:
        log_dir = Path.home() / ".local" / "share" / "personal-index" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / f"personal-index-{datetime.now().strftime('%Y%m%d')}.log")

    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s (%(module)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        pass  # Silently skip file logging if not available

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module."""
    return logging.getLogger(f"personal_index.{name}")
