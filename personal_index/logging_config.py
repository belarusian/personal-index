"""Logging configuration for personal-index."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    verbose: bool = False,
    log_file: Optional[str] = None,
):
    """Configure logging for the personal_index package."""
    if verbose:
        level = "DEBUG"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger("personal_index")
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(f"personal_index.{name}")
