"""Integration tests for content filtering."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.content_filter import ContentFilter


class TestFilteringIntegration:
    """Test content filtering end-to-end."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_filter_via_pipeline(self):
        """Content should be filtered through the pipeline."""
        result = self.app.process_content(
            "https://example.com",
            "Meaningful content about technology",
            "Tech Article",
        )
        assert "passes_filter" in result

    def test_filter_direct(self):
        """ContentFilter should work directly."""
        filter_ = ContentFilter()
        assert isinstance(filter_.should_index("Some content"), bool)

    def test_filter_empty_content(self):
        """Empty content should be handled by filter."""
        filter_ = ContentFilter()
        result = filter_.should_index("")
        assert isinstance(result, bool)

    def test_filter_short_content(self):
        """Very short content should be handled by filter."""
        filter_ = ContentFilter()
        result = filter_.should_index("Hi")
        assert isinstance(result, bool)

    def test_filter_long_content(self):
        """Long content should be handled by filter."""
        filter_ = ContentFilter()
        result = filter_.should_index("Word " * 1000)
        assert isinstance(result, bool)
