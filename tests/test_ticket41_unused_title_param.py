"""Test for TICKET-41: title parameter in _check_single_item() is unused."""
import inspect
from personal_index.content_dedup import ContentDeduplicator


class TestUnusedTitleParam:
    """Test that the unused title parameter is properly marked."""

    def test_title_param_is_prefixed_with_underscore(self):
        """The unused title parameter should be prefixed with underscore."""
        sig = inspect.signature(ContentDeduplicator._check_single_item)
        params = list(sig.parameters.keys())
        # Should have self, url, _title, content
        assert "_title" in params, f"Expected '_title' in params, got {params}"
        assert "title" not in params, f"'title' should be renamed to '_title', got {params}"

    def test_check_single_item_still_works(self):
        """_check_single_item should still work correctly with positional args."""
        dedup = ContentDeduplicator()
        result = dedup._check_single_item("https://example.com", "Some Title", "unique content here")
        assert result is not None
        assert result.is_duplicate is False

    def test_check_single_item_detects_duplicates(self):
        """_check_single_item should detect exact duplicates."""
        dedup = ContentDeduplicator()
        result1 = dedup._check_single_item("https://example.com/1", "Title 1", "same content")
        result2 = dedup._check_single_item("https://example.com/2", "Title 2", "same content")
        assert result1.is_duplicate is False
        assert result2.is_duplicate is True
