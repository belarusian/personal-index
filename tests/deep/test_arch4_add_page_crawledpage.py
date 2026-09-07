"""Adversarial VERIFY for ARCH-4: SearchIndex.add_page CrawledPage path.

ARCH-4's public contract (tickets/ARCH-4.md) states the guard path accepts
BOTH IndexedPage and CrawledPage, and that a CrawledPage is converted to an
IndexedPage with:
  - domain via url_utils.extract_domain
  - content_length = len(content)
  - crawled_at isoformat'd when it has one
  - score from relevance_score
and that add_page returns the new page count len(self._pages) (an int), NOT a
page id.

The implementer's pinning test (tests/test_index.py::test_add_page_returns_count_pinned)
only exercises the IndexedPage branch. This file attacks the untested
CrawledPage branch with guard inputs the contract implies.
"""

from datetime import datetime, timezone

import pytest

from personal_index.index import SearchIndex
from personal_index.models import CrawledPage


@pytest.fixture
def search_index(tmp_path):
    db_path = str(tmp_path / "deep_index.db")
    idx = SearchIndex(db_path=db_path)
    yield idx
    idx.close()


def _crawl(url, title="T", content="body", score=0.7, crawled_at=None):
    return CrawledPage(
        url=url,
        title=title,
        content=content,
        relevance_score=score,
        crawled_at=crawled_at if crawled_at is not None else datetime.now(timezone.utc),
    )


class TestAddPageCrawledPageContract:
    def test_crawledpage_returns_count_not_id(self, search_index):
        """Contract: return is the new page count (int), not a page id."""
        r1 = search_index.add_page(_crawl("https://a.example/1"))
        assert r1 == 1
        r2 = search_index.add_page(_crawl("https://a.example/2"))
        assert r2 == 2
        # overwrite same url -> count unchanged
        r3 = search_index.add_page(_crawl("https://a.example/1", title="upd"))
        assert r3 == 2

    def test_crawledpage_conversion_fields(self, search_index):
        """Contract: domain/content_length/score/crawled_at conversion."""
        dt = datetime(2024, 5, 1, 12, 30, 0, tzinfo=timezone.utc)
        page = _crawl("https://sub.example.com:8080/path?q=1", title="Hi",
                      content="some content here", score=0.42, crawled_at=dt)
        search_index.add_page(page)
        stored = search_index.get_page("https://sub.example.com:8080/path?q=1")
        assert stored is not None
        # domain via extract_domain (port stripped, lowercased)
        assert stored.domain == "sub.example.com"
        # content_length = len(content)
        assert stored.content_length == len("some content here")
        # score from relevance_score
        assert stored.score == pytest.approx(0.42)
        # crawled_at isoformat'd (string, not datetime)
        assert isinstance(stored.crawled_at, str)
        assert stored.crawled_at == dt.isoformat()

    def test_crawledpage_empty_content(self, search_index):
        """Guard input: empty content -> content_length 0, content ''."""
        page = _crawl("https://empty.example/x", content="")
        search_index.add_page(page)
        stored = search_index.get_page("https://empty.example/x")
        assert stored is not None
        assert stored.content == ""
        assert stored.content_length == 0

    def test_crawledpage_none_content(self, search_index):
        """Guard input: content=None (contract: content or '') -> '' and 0."""
        page = CrawledPage(url="https://none.example/y", title="N", content=None)
        search_index.add_page(page)
        stored = search_index.get_page("https://none.example/y")
        assert stored is not None
        assert stored.content == ""
        assert stored.content_length == 0

    def test_crawledpage_unicode_content(self, search_index):
        """Guard input: unicode content round-trips and length is char count."""
        content = "привет мир — ünïcödé"
        page = _crawl("https://uni.example/z", content=content)
        search_index.add_page(page)
        stored = search_index.get_page("https://uni.example/z")
        assert stored is not None
        assert stored.content == content
        assert stored.content_length == len(content)

    def test_crawledpage_no_crawled_at(self, search_index):
        """Guard input: crawled_at='' (no isoformat) stays a string, no crash."""
        page = CrawledPage(url="https://noat.example/w", title="W",
                           content="c", crawled_at="")
        search_index.add_page(page)
        stored = search_index.get_page("https://noat.example/w")
        assert stored is not None
        # contract: crawled_at isoformat'd WHEN IT HAS ONE; '' has none -> ''
        assert stored.crawled_at == ""
