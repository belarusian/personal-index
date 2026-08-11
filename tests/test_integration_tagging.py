"""Integration tests for content tagging."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.content_tagger import ContentTagger


class TestTaggingIntegration:
    """Test content tagging end-to-end."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_tagging_via_pipeline(self):
        """Content should be tagged through the pipeline."""
        result = self.app.process_content(
            "https://example.com",
            "Python programming tutorial",
            "Python Tutorial",
        )
        assert "tags" in result
        assert isinstance(result["tags"], list)

    def test_tagging_direct(self):
        """ContentTagger should work directly."""
        tagger = ContentTagger()
        tags = tagger.tag("Python programming tutorial", min_confidence=0.5)
        assert isinstance(tags.tags, list)

    def test_tagging_empty_content(self):
        """Empty content should return empty or minimal tags."""
        tagger = ContentTagger()
        tags = tagger.tag("", min_confidence=0.5)
        assert isinstance(tags.tags, list)

    def test_tagging_consistent(self):
        """Same content should produce same tags."""
        tagger = ContentTagger()
        tags1 = tagger.tag("Python programming", min_confidence=0.5)
        tags2 = tagger.tag("Python programming", min_confidence=0.5)
        assert tags1.tags == tags2.tags
