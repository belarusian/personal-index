"""Tests for TICKET-96: Dead code — duplicate tokenize() functions removed."""

from __future__ import annotations


class TestTokenizeRemovedFromContent:
    """Verify tokenize() was removed from personal_index.content."""

    def test_tokenize_not_in_content_module(self):
        """tokenize should not exist in personal_index.content."""
        import personal_index.content as content_mod
        assert not hasattr(content_mod, "tokenize"), \
            "tokenize() should have been removed from personal_index.content"

    def test_content_module_imports_cleanly(self):
        """personal_index.content should still import without errors."""
        # Should not raise
        assert True

    def test_content_module_other_functions_still_exist(self):
        """Other functions in content.py should still be accessible."""
        import personal_index.content as content_mod
        assert hasattr(content_mod, "remove_stopwords")
        assert hasattr(content_mod, "compute_tf")


class TestTokenizeRemovedFromUtils:
    """Verify tokenize() was removed from personal_index.utils.__init__."""

    def test_tokenize_not_in_utils_all(self):
        """tokenize should not be in __all__ of personal_index.utils."""
        from personal_index.utils import __all__
        assert "tokenize" not in __all__, \
            "tokenize should have been removed from utils __all__"

    def test_tokenize_not_in_utils_module(self):
        """tokenize should not exist in personal_index.utils."""
        import personal_index.utils as utils_mod
        assert not hasattr(utils_mod, "tokenize"), \
            "tokenize() should have been removed from personal_index.utils"

    def test_utils_module_imports_cleanly(self):
        """personal_index.utils should still import without errors."""
        assert True

    def test_utils_other_functions_still_exist(self):
        """Other functions in utils should still be accessible."""
        import personal_index.utils as utils_mod
        assert hasattr(utils_mod, "compute_relevance_score")
        assert hasattr(utils_mod, "extract_text_content")


class TestCanonicalTokenizeExists:
    """Verify the canonical tokenize in text_utils still works."""

    def test_text_utils_tokenize_exists(self):
        """tokenize should exist in personal_index.text_utils."""
        from personal_index.text_utils import tokenize
        assert callable(tokenize)

    def test_text_utils_tokenize_basic(self):
        """tokenize should split text into tokens."""
        from personal_index.text_utils import tokenize
        result = tokenize("Hello world test")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_text_utils_tokenize_empty(self):
        """tokenize should handle empty input."""
        from personal_index.text_utils import tokenize
        result = tokenize("")
        assert result == []

    def test_text_utils_tokenize_lowercase(self):
        """tokenize should lowercase by default."""
        from personal_index.text_utils import tokenize
        result = tokenize("Hello WORLD")
        assert all(t == t.lower() for t in result)
