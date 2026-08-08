"""Integration tests for Personal Index."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from personal_index.config import AppConfig, Interest, CrawlerConfig
from personal_index.filter import ContentFilter
from personal_index.indexer import SearchIndex
from personal_index.models import Page
from personal_index.crawler import WebCrawler


class TestFullPipeline:
    """Test the full crawl-filter-index-search pipeline."""

    def test_crawl_filter_index_search(self, tmp_path: Path) -> None:
        """Test complete pipeline: crawl -> filter -> index -> search."""
        config = AppConfig(config_dir=tmp_path, index_dir=tmp_path / "index")
        config.interests.append(
            Interest(topic="AI", keywords=["artificial intelligence", "machine learning"])
        )

        # Create content filter
        content_filter = ContentFilter(config.interests, min_relevance_score=0.0)

        # Create search index
        index = SearchIndex(index_dir=config.index_dir)

        # Simulate crawled pages
        pages = [
            Page(
                url="https://example.com/ai-article",
                title="Introduction to AI",
                content="Artificial intelligence and machine learning are transforming technology.",
            ),
            Page(
                url="https://example.com/recipe",
                title="Baking Bread",
                content="This recipe for baking bread is simple and delicious.",
            ),
            Page(
                url="https://example.com/ml-guide",
                title="Machine Learning Guide",
                content="A comprehensive guide to machine learning algorithms.",
            ),
        ]

        # Filter pages
        filtered_pages = []
        for page in pages:
            result = content_filter.filter_page(page)
            content_filter.update_page(page, result)
            if result.passed:
                filtered_pages.append(page)

        # Only AI-related pages should pass
        assert len(filtered_pages) == 2

        # Index filtered pages
        for page in filtered_pages:
            index.add_page(page)

        # Search
        results = index.search("machine learning")
        assert len(results) == 2
        for result in results:
            assert "AI" in result.page.matched_interests

    def test_crawl_with_mock_fetch(self, tmp_path: Path) -> None:
        """Test crawler with mocked HTTP fetch."""
        config = AppConfig(config_dir=tmp_path, index_dir=tmp_path / "index")
        config.crawler = CrawlerConfig(politeness_delay=0)
        config.interests.append(Interest(topic="test", keywords=["hello"]))

        content_filter = ContentFilter(config.interests, min_relevance_score=0.0)
        crawler = WebCrawler(config=config, content_filter=content_filter)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.text = "<html><head><title>Hello World</title></head><body><p>Hello world test</p></body></html>"
        mock_response.headers = {"Content-Type": "text/html"}

        with patch.object(crawler.session, "get", return_value=mock_response):
            pages = crawler.crawl(["https://example.com"], max_depth=0)
            assert len(pages) == 1
            assert pages[0].title == "Hello World"

        crawler.close()

    def test_save_and_restore_index(self, tmp_path: Path) -> None:
        """Test that index can be saved and restored."""
        index_dir = tmp_path / "index"
        index = SearchIndex(index_dir=index_dir)

        # Add pages
        for i in range(5):
            index.add_page(
                Page(
                    url=f"https://example.com/page{i}",
                    title=f"Page {i}",
                    content=f"Content for page {i} about testing.",
                )
            )

        # Save
        index.save()

        # Load into new index
        restored = SearchIndex(index_dir=index_dir)
        restored.load()

        assert restored.num_documents == 5
        results = restored.search("testing")
        assert len(results) == 5

    def test_config_save_and_load(self, tmp_path: Path) -> None:
        """Test config persistence."""
        config = AppConfig(config_dir=tmp_path)
        config.interests.append(
            Interest(
                topic="Technology",
                keywords=["AI", "ML"],
                priority=8,
            )
        )
        config.crawler.max_depth = 5
        config.save()

        # Load fresh
        loaded = AppConfig.load(tmp_path / "config.json")
        assert len(loaded.interests) == 1
        assert loaded.interests[0].topic == "Technology"
        assert loaded.crawler.max_depth == 5
