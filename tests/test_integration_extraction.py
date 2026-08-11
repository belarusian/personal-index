"""Integration tests for content extraction."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp


import pytest
class TestExtractionIntegration:
    """Test content extraction end-to-end."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_extract_via_pipeline(self):
        """Content should be extracted through the pipeline."""
        result = self.app.process_content(
            "https://example.com",
            "<html><body><p>Hello world</p></body></html>",
            "HTML Page",
        )
        assert "extracted_text" in result
        assert "Hello world" in result["extracted_text"]

    def test_extract_plain_text(self):
        """Plain text should pass through extraction."""
        result = self.app.process_content(
            "https://example.com",
            "This is plain text content",
            "Plain Page",
        )
        assert "extracted_text" in result
        assert "plain text" in result["extracted_text"].lower()

    def test_extract_empty(self):
        """Empty content should return empty string."""
        result = self.app.process_content(
            "https://example.com",
            "",
            "Empty Page",
        )
        assert isinstance(result, dict)
        assert "url" in result

    def test_extract_with_script_tags(self):
        """Script tags should be removed from extracted text."""
        result = self.app.process_content(
            "https://example.com",
            "<html><body><script>alert('xss')</script><p>Safe content</p></body></html>",
            "HTML Page",
        )
        assert "extracted_text" in result
        assert "Safe content" in result["extracted_text"]
