"""Integration tests for content extraction."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.content_extractor import extract_text


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

    def test_extract_direct(self):
        """extract_text should work directly."""
        text = extract_text("<html><body><p>Test content</p></body></html>")
        assert "Test content" in text

    def test_extract_plain_text(self):
        """Plain text should pass through extraction."""
        text = extract_text("This is plain text")
        assert "plain text" in text.lower()

    def test_extract_empty(self):
        """Empty content should return empty string."""
        text = extract_text("")
        assert text == ""

    def test_extract_with_script_tags(self):
        """Script tags should be removed."""
        text = extract_text("<html><body><script>alert('xss')</script><p>Safe</p></body></html>")
        assert "Safe" in text
        assert "alert" not in text

    def test_extract_with_style_tags(self):
        """Style tags should be removed."""
        text = extract_text("<html><body><style>.red { color: red; }</style><p>Content</p></body></html>")
        assert "Content" in text
        assert "color" not in text.lower() or "content" in text.lower()
