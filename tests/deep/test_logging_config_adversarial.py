"""Adversarial deep tests for personal_index.logging_config.setup_logging.

ARCH-95 contract (fail-loud on unknown logging level):
  - An unrecognized level string must raise ValueError naming the offending
    string, and must NOT silently coerce the root logger to INFO.
  - Every valid level (and the verbose=True override) must still work.

This file is the validator's regression armor for the ARCH-95 fix
(raise ValueError when getattr(logging, level.upper(), None) is not an int).
"""

import logging

import pytest

from personal_index.logging_config import setup_logging


def _root_level() -> int:
    return logging.getLogger("personal_index").level


class TestUnknownLevelRaises:
    """The fail-loud contract: unknown level strings raise ValueError."""

    @pytest.mark.parametrize(
        "bad",
        [
            "WARNIN",   # typo of WARNING
            "",         # empty string -> .upper() == "" -> not a logging attr
            "TRACE",    # not a standard logging level
            "VERBOSE",  # not a logging module attribute
            "CRITICALX",
            "DEBUGG",
            "ERR",      # not a logging module attribute in this stdlib
            "CRIT",     # not a logging module attribute in this stdlib
            "   ",      # whitespace-only
        ],
    )
    def test_unknown_level_raises_valueerror(self, bad):
        # Pre-set the root logger to a sentinel so we can prove the failed
        # call did NOT coerce it to INFO.
        logger = logging.getLogger("personal_index")
        logger.setLevel(logging.ERROR)
        with pytest.raises(ValueError):
            setup_logging(level=bad)
        # The failed call must not have touched the level.
        assert logger.level == logging.ERROR

    def test_error_message_names_offending_string(self):
        with pytest.raises(ValueError, match="WARNIN"):
            setup_logging(level="WARNIN")

    def test_case_insensitive_lookup_still_works(self):
        # Lowercase valid levels must still be honored (upper() lookup).
        setup_logging(level="info")
        assert _root_level() == logging.INFO
        setup_logging(level="debug")
        assert _root_level() == logging.DEBUG


class TestValidLevelsStillHonored:
    """The fix must not regress any valid level."""

    @pytest.mark.parametrize(
        "lv",
        ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL",
         "WARN", "FATAL", "NOTSET"],
    )
    def test_valid_level_sets_root(self, lv):
        setup_logging(level=lv)
        assert _root_level() == getattr(logging, lv)

    def test_default_is_info(self):
        setup_logging()
        assert _root_level() == logging.INFO

    def test_verbose_forces_debug(self):
        setup_logging(verbose=True)
        assert _root_level() == logging.DEBUG

    def test_verbose_with_bad_level_does_not_raise(self):
        # verbose=True hard-codes level="DEBUG" before the lookup, so even a
        # bad level string is overridden and must not raise.
        setup_logging(level="NOT_A_LEVEL", verbose=True)
        assert _root_level() == logging.DEBUG

    def test_verbose_with_info_does_not_raise(self):
        setup_logging("INFO", verbose=True)
        assert _root_level() == logging.DEBUG


class TestIdempotenceAndHandlers:
    """The idempotent handler reset must survive repeated calls."""

    def test_repeated_calls_do_not_accumulate_handlers(self):
        setup_logging(level="INFO")
        logger = logging.getLogger("personal_index")
        first = len(logger.handlers)
        setup_logging(level="INFO")
        setup_logging(level="INFO")
        assert len(logger.handlers) == first

    def test_roundtrip_level_change(self):
        setup_logging(level="DEBUG")
        assert _root_level() == logging.DEBUG
        setup_logging(level="CRITICAL")
        assert _root_level() == logging.CRITICAL
        setup_logging(level="INFO")
        assert _root_level() == logging.INFO
