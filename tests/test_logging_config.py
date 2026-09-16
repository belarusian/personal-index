"""Tests for personal_index.logging_config."""

import logging
from pathlib import Path

import pytest

from personal_index.logging_config import get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging."""

    def test_default_setup(self):
        setup_logging()
        logger = logging.getLogger("personal_index")
        assert logger.level == logging.INFO

    def test_verbose_setup(self):
        setup_logging(verbose=True)
        logger = logging.getLogger("personal_index")
        assert logger.level == logging.DEBUG

    def test_custom_level(self):
        setup_logging(level="WARNING")
        logger = logging.getLogger("personal_index")
        assert logger.level == logging.WARNING

    def test_unknown_level_raises(self):
        logger = logging.getLogger("personal_index")
        logger.setLevel(logging.ERROR)
        with pytest.raises(ValueError, match="VERBOSE"):
            setup_logging(level="VERBOSE")
        # The failed call must not have coerced the level to INFO.
        assert logger.level == logging.ERROR

    @pytest.mark.parametrize(
        "lv", ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]
    )
    def test_valid_levels_still_honored(self, lv):
        setup_logging(level=lv)
        logger = logging.getLogger("personal_index")
        assert logger.level == getattr(logging, lv)

    def test_file_handler(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        setup_logging(log_file=log_file)
        logger = logging.getLogger("personal_index")
        logger.info("Test message")
        logger.handlers[0].flush()
        if len(logger.handlers) > 1:
            logger.handlers[1].flush()
        # Check file was created
        assert Path(log_file).exists()


class TestGetLogger:
    """Tests for get_logger."""

    def test_get_logger(self):
        logger = get_logger("test_module")
        assert logger.name == "personal_index.test_module"
        assert isinstance(logger, logging.Logger)
