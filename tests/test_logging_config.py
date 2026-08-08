"""Tests for the logging configuration module."""

import logging
import pytest
from personal_index.logging_config import setup_logging, get_logger


class TestSetupLogging:
    def test_default_setup(self, tmp_path, capsys):
        logger = setup_logging()
        assert logger.name == "personal_index"
        assert len(logger.handlers) >= 1

    def test_verbose_mode(self, tmp_path):
        logger = setup_logging(verbose=True)
        assert logger.level == logging.DEBUG

    def test_custom_level(self, tmp_path):
        logger = setup_logging(level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_custom_log_file(self, tmp_path):
        log_file = str(tmp_path / "custom.log")
        logger = setup_logging(log_file=log_file)
        assert len(logger.handlers) >= 2

    def test_logging_output(self, tmp_path, capsys):
        log_file = str(tmp_path / "test.log")
        logger = setup_logging(log_file=log_file)
        logger.info("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_logger_hierarchy(self, tmp_path):
        setup_logging()
        child = get_logger("crawler")
        assert child.name == "personal_index.crawler"

    def test_multiple_setup_clears_handlers(self, tmp_path):
        logger = setup_logging()
        initial_count = len(logger.handlers)
        logger = setup_logging()
        assert len(logger.handlers) == initial_count


class TestGetLogger:
    def test_get_logger_name(self, tmp_path):
        setup_logging()
        logger = get_logger("test_module")
        assert logger.name == "personal_index.test_module"

    def test_get_logger_returns_same(self, tmp_path):
        setup_logging()
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2
