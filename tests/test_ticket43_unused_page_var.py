"""Test for TICKET-43: page variable in remove() is assigned but never used."""
import inspect
from personal_index.search_index import SearchIndex


class TestUnusedPageVariable:
    """Test that the unused page variable is removed from remove()."""

    def test_no_page_assignment_in_remove(self):
        """The remove() method should not assign to a 'page' variable."""
        source = inspect.getsource(SearchIndex.remove)
        # Check that there's no 'page =' assignment in the source
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("page ="):
                assert False, f"Found unused 'page' assignment: {stripped}"

    def test_remove_still_works(self, tmp_path):
        """remove() should still correctly remove pages from the index."""
        from personal_index.models import CrawledPage
        index = SearchIndex(str(tmp_path / "test_index"))
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="Hello world",
        )
        index.add(page)
        assert index.count() == 1
        result = index.remove("https://example.com")
        assert result is True
        assert index.count() == 0

    def test_remove_returns_false_for_missing_url(self, tmp_path):
        """remove() should return False for URLs not in the index."""
        index = SearchIndex(str(tmp_path / "test_index2"))
        result = index.remove("https://nonexistent.com")
        assert result is False

    def test_no_noqa_f841_in_remove(self):
        """The remove() method should not have noqa: F841 suppression."""
        source = inspect.getsource(SearchIndex.remove)
        assert "noqa: F841" not in source, "Found noqa: F841 in remove()"
