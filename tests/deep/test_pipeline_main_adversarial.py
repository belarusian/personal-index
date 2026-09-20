"""Adversarial deep tests for the main Pipeline class (pipeline.py).

Tests edge cases in the crawl→extract→filter→score→tag→index pipeline.
"""

import os
import tempfile
import pytest
from personal_index.pipeline import Pipeline, PipelineConfig
from personal_index.models import CrawledPage, Interest


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def pipeline(tmp_data_dir):
    return Pipeline(data_dir=tmp_data_dir)


def test_empty_seed_urls(pipeline):
    """Pipeline with no seed URLs should succeed with zero pages."""
    stats = pipeline.run([])
    assert stats.pages_crawled == 0
    assert stats.pages_indexed == 0


def test_add_page_directly_empty_content(pipeline):
    """Adding a page with no content should return False."""
    page = CrawledPage(url="http://example.com/empty", title="Empty", content="")
    result = pipeline.add_page_directly(page)
    assert result is False


def test_add_page_directly_whitespace_content(pipeline):
    """Adding a page with whitespace-only content should return False."""
    page = CrawledPage(url="http://example.com/ws", title="WS", content="   \n  ")
    result = pipeline.add_page_directly(page)
    assert result is False


def test_add_page_directly_unicode(pipeline):
    """Adding a page with unicode content should succeed."""
    # Need 100+ chars to pass filter; add interest to pass interest filter
    pipeline.interest_store.add(Interest(name="test", keywords=["テスト"]))
    content = "日本語のテストコンテンツです。" * 10
    page = CrawledPage(
        url="http://example.com/unicode",
        title="Привет мир",
        content=content
    )
    result = pipeline.add_page_directly(page)
    assert result is True


def test_add_page_directly_duplicate_url(pipeline):
    """Adding the same URL twice should not crash (idempotence)."""
    pipeline.interest_store.add(Interest(name="test", keywords=["test"]))
    content = "Some content here for the duplicate test. " * 10
    page = CrawledPage(
        url="http://example.com/dup",
        title="Duplicate",
        content=content
    )
    result1 = pipeline.add_page_directly(page)
    result2 = pipeline.add_page_directly(page)
    # Should not crash; second add may fail or succeed depending on implementation
    assert isinstance(result1, bool)
    assert isinstance(result2, bool)


def test_search_empty_query(pipeline):
    """Search with empty query should not crash."""
    results = pipeline.search("")
    assert isinstance(results, list)


def test_search_whitespace_query(pipeline):
    """Search with whitespace query should not crash."""
    results = pipeline.search("   ")
    assert isinstance(results, list)


def test_search_negative_limit(pipeline):
    """Search with negative limit should not crash."""
    results = pipeline.search("test", limit=-5)
    assert isinstance(results, list)


def test_search_zero_limit(pipeline):
    """Search with zero limit should return empty list."""
    results = pipeline.search("test", limit=0)
    assert isinstance(results, list)
    assert len(results) == 0


def test_search_unicode_query(pipeline):
    """Search with unicode query should not crash."""
    results = pipeline.search("テスト")
    assert isinstance(results, list)


def test_get_stats(pipeline):
    """get_stats should return a dict."""
    stats = pipeline.get_stats()
    assert isinstance(stats, dict)


def test_pipeline_config_defaults(pipeline):
    """Pipeline should have sensible default config."""
    assert pipeline.config is not None
    assert isinstance(pipeline.config, PipelineConfig)


def test_add_page_with_html_extraction(pipeline):
    """Page with raw_html should have content extracted."""
    pipeline.interest_store.add(Interest(name="test", keywords=["test"]))
    long_body = "Body text here for the test. " * 20
    page = CrawledPage(
        url="http://example.com/html",
        title="",
        content="",
        raw_html=f"<html><head><title>Test Page</title></head><body><h1>Title</h1><p>{long_body}</p></body></html>"
    )
    result = pipeline.add_page_directly(page)
    assert result is True
    # Content should have been extracted
    assert page.content is not None
    assert len(page.content) > 0
