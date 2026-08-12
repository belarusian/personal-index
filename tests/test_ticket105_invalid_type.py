"""Tests for TICKET-105: Fix invalid type usage in content_tagger/tagger.py."""

from __future__ import annotations

import subprocess
import sys

from personal_index.content_tagger.tagger import ContentTagger, TagResult


class TestTicket105InvalidType:
    """Verify mypy valid-type errors are fixed in tagger.py."""

    def test_mypy_no_valid_type_error(self):
        """tagger.py should have no mypy valid-type errors."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy",
             "personal_index/content_tagger/tagger.py",
             "--no-error-summary"],
            capture_output=True,
            text=True,
        )
        assert "valid-type" not in result.stdout, (
            f"tagger.py still has valid-type errors:\n{result.stdout}"
        )

    def test_tag_result_is_class_not_variable(self):
        """TagResult should be accessible as a module-level class."""
        assert isinstance(TagResult, type), "TagResult should be a class"

    def test_tag_result_instantiation(self):
        """TagResult should be instantiable."""
        result = TagResult(content="test", tags=[])
        assert result.content == "test"
        assert result.tags == []

    def test_content_tagger_tag_returns_tag_result(self):
        """ContentTagger.tag() should return TagResult instances."""
        tagger = ContentTagger()
        result = tagger.tag("python programming code")
        assert isinstance(result, TagResult)

    def test_content_tagger_batch_tag_returns_list_of_tag_results(self):
        """ContentTagger.batch_tag() should return list of TagResult."""
        tagger = ContentTagger()
        results = tagger.batch_tag(["python code", "javascript web"])
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, TagResult)

    def test_tag_result_from_dict(self):
        """TagResult.from_dict should work correctly."""
        data = {"tags": [{"name": "test", "confidence": 0.8}], "content": "test content"}
        result = TagResult.from_dict(data)
        assert len(result.tags) == 1
        assert result.tags[0].name == "test"
        assert result.content == "test content"
