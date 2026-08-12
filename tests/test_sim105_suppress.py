"""Tests for TICKET-71: SIM105 - try/except/pass replaced with contextlib.suppress."""

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage


class TestContentFilter:
    def test_invalid_regex_suppressed(self):
        """Invalid regex patterns should be silently ignored via suppress."""
        config = FilterConfig(blocked_patterns=["[invalid(", "spam"])
        cf = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com",
            title="Spam Page",
            content="this has spam",
        )
        assert cf.should_include(page) is False

    def test_compile_patterns_skips_invalid(self):
        """_compile_patterns should skip invalid regex patterns."""
        patterns = ContentFilter._compile_patterns(["[invalid(", "valid_pattern", "(broken"])
        assert len(patterns) == 1
        assert patterns[0].pattern == "valid_pattern"


class TestInterestStore:
    def test_load_from_invalid_json(self):
        """Invalid JSON should be silently ignored via suppress."""
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json")
            f.flush()
            store = InterestStore(store_path=f.name)
            assert store.get_all_topics() == set()
            os.unlink(f.name)
