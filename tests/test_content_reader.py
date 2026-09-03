"""Tests for content reader module."""

from __future__ import annotations

import pytest

from personal_index.content_reader import (
    ContentReader,
    PageView,
    ReadResult,
)


def make_item(url: str, title: str, content: str = "", tags: list[str] | None = None, score: float = 0.0) -> ReadResult:
    return ReadResult(
        url=url,
        title=title,
        content=content,
        tags=tags or [],
        score=score,
    )


class TestReadResult:
    def test_to_dict(self):
        item = ReadResult(url="https://x.com", title="Test", content="body", tags=["a"], score=5.0)
        d = item.to_dict()
        assert d["url"] == "https://x.com"
        assert d["title"] == "Test"
        assert d["content"] == "body"
        assert d["tags"] == ["a"]
        assert d["score"] == 5.0


class TestPageView:
    def test_pagination_indices(self):
        view = PageView(
            items=[], page=2, page_size=10,
            total_items=25, total_pages=3,
            has_next=True, has_prev=True,
        )
        assert view.start_index == 10
        assert view.end_index == 20

    def test_first_page(self):
        view = PageView(
            items=[], page=1, page_size=10,
            total_items=25, total_pages=3,
            has_next=True, has_prev=False,
        )
        assert view.start_index == 0
        assert view.end_index == 10


class TestContentReader:
    def setup_method(self):
        self.reader = ContentReader()
        self.reader.add_many([
            make_item("https://a.com", "Alpha", "Alpha content", tags=["tech"], score=8.0),
            make_item("https://b.com", "Beta", "Beta content", tags=["tech", "science"], score=6.0),
            make_item("https://c.com", "Gamma", "Gamma content", tags=["science"], score=9.0),
            make_item("https://d.com", "Delta", "Delta content", tags=["art"], score=3.0),
        ])

    def test_add_and_get(self):
        item = make_item("https://new.com", "New")
        self.reader.add(item)
        result = self.reader.get("https://new.com")
        assert result is not None
        assert result.title == "New"

    def test_get_missing(self):
        assert self.reader.get("https://missing.com") is None

    def test_list_all(self):
        assert len(self.reader.list_all()) == 4

    def test_paginate_default(self):
        view = self.reader.paginate(page=1, page_size=2)
        assert len(view.items) == 2
        assert view.total_pages == 2
        assert view.has_next is True
        assert view.has_prev is False

    def test_paginate_second_page(self):
        view = self.reader.paginate(page=2, page_size=2)
        assert len(view.items) == 2
        assert view.has_next is False
        assert view.has_prev is True

    def test_paginate_sort_by_title(self):
        view = self.reader.paginate(page=1, page_size=10, sort_by="title", reverse=False)
        titles = [i.title for i in view.items]
        assert titles == sorted(titles)

    def test_paginate_out_of_range(self):
        view = self.reader.paginate(page=100, page_size=10)
        assert view.page == 1  # clamped to last page

    def test_paginate_zero_page_size_raises(self):
        with pytest.raises(ValueError, match="Page size must be >= 1"):
            self.reader.paginate(page=1, page_size=0)

    def test_paginate_negative_page_size_raises(self):
        with pytest.raises(ValueError, match="Page size must be >= 1"):
            self.reader.paginate(page=1, page_size=-5)

    def test_filter_by_tags_any(self):
        results = self.reader.filter_by_tags(["tech"], match_all=False)
        urls = [r.url for r in results]
        assert "https://a.com" in urls
        assert "https://b.com" in urls
        assert "https://c.com" not in urls

    def test_filter_by_tags_all(self):
        results = self.reader.filter_by_tags(["tech", "science"], match_all=True)
        urls = [r.url for r in results]
        assert "https://b.com" in urls
        assert "https://a.com" not in urls

    def test_filter_by_tags_empty(self):
        results = self.reader.filter_by_tags([], match_all=False)
        assert len(results) == 4

    def test_filter_by_score_min(self):
        results = self.reader.filter_by_score(min_score=7.0)
        assert len(results) == 2
        assert all(r.score >= 7.0 for r in results)

    def test_filter_by_score_range(self):
        results = self.reader.filter_by_score(min_score=5.0, max_score=8.0)
        assert len(results) == 2

    def test_search_titles(self):
        results = self.reader.search_titles("alpha")
        assert len(results) == 1
        assert results[0].title == "Alpha"

    def test_search_titles_case_insensitive(self):
        results = self.reader.search_titles("ALPHA")
        assert len(results) == 1

    def test_search_content(self):
        results = self.reader.search_content("Gamma")
        assert len(results) == 1
        assert results[0].url == "https://c.com"

    def test_format_item(self):
        item = make_item("https://x.com", "Test", "Some content here", tags=["tag1"], score=5.0)
        formatted = self.reader.format_item(item)
        assert "Test" in formatted
        assert "https://x.com" in formatted
        assert "tag1" in formatted
        assert "Some content here" in formatted

    def test_format_item_no_content(self):
        item = make_item("https://x.com", "Test", "", tags=[], score=0.0)
        formatted = self.reader.format_item(item)
        assert "Test" in formatted
        assert "Tags:" not in formatted

    def test_format_page(self):
        view = self.reader.paginate(page=1, page_size=2)
        formatted = self.reader.format_page(view)
        assert "Page 1 of 2" in formatted
        assert "Next Page" in formatted

    def test_clear(self):
        self.reader.clear()
        assert self.reader.count == 0
        assert self.reader.list_all() == []

    def test_count(self):
        assert self.reader.count == 4
