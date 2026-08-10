"""Tests for TICKET-95: Broad exception handling fixes."""

from __future__ import annotations

import logging
import pytest
from unittest.mock import patch, MagicMock

from personal_index.export_markdown import save_markdown
from personal_index.url_utils import is_valid_url


class TestSaveMarkdownLogsErrors:
    """Test that save_markdown logs errors instead of silently swallowing them."""

    def test_save_markdown_logs_on_exception(self, tmp_path, caplog):
        """save_markdown should log an error when an exception occurs."""
        caplog.set_level(logging.ERROR)
        bad_filepath = str(tmp_path / "nonexistent_dir" / "subdir" / "test.md")
        
        # Patch Path.write_text to raise an exception
        with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
            result = save_markdown({"title": "Test"}, bad_filepath)
        
        assert result is False
        assert any("Failed to save markdown" in record.message for record in caplog.records)
        assert any("Permission denied" in record.message for record in caplog.records)

    def test_save_markdown_logs_exception_type(self, tmp_path, caplog):
        """save_markdown should include the exception details in the log."""
        caplog.set_level(logging.ERROR)
        bad_filepath = str(tmp_path / "test.md")
        
        with patch("pathlib.Path.write_text", side_effect=ValueError("bad data")):
            result = save_markdown({"title": "Test"}, bad_filepath)
        
        assert result is False
        assert any("bad data" in record.message for record in caplog.records)

    def test_save_markdown_success_no_log(self, tmp_path, caplog):
        """save_markdown should not log on success."""
        caplog.set_level(logging.ERROR)
        filepath = str(tmp_path / "success.md")
        
        result = save_markdown({"title": "Test"}, filepath)
        
        assert result is True
        assert not any("Failed to save markdown" in record.message for record in caplog.records)


class TestIsValidUrlNarrowException:
    """Test that is_valid_url only catches specific exceptions (not bare Exception)."""

    def test_valid_http_url(self):
        assert is_valid_url("http://example.com") is True

    def test_valid_https_url(self):
        assert is_valid_url("https://example.com/path") is True

    def test_invalid_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_invalid_file_scheme(self):
        assert is_valid_url("file:///etc/passwd") is False

    def test_invalid_empty_string(self):
        assert is_valid_url("") is False

    def test_invalid_none(self):
        assert is_valid_url(None) is False

    def test_value_error_handled(self):
        """ValueError should be caught and return False."""
        assert is_valid_url("") is False

    def test_attribute_error_handled(self):
        """AttributeError should be caught and return False."""
        assert is_valid_url(None) is False

    def test_unexpected_exception_not_swallowed(self):
        """Non-ValueError/AttributeError exceptions should propagate, not be swallowed."""
        with patch("personal_index.url_utils.urlparse", side_effect=RuntimeError("unexpected")):
            with pytest.raises(RuntimeError, match="unexpected"):
                is_valid_url("http://example.com")
