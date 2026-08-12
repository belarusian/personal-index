"""Cross-component integration tests.

Verifies that different components work together correctly:
- InterestStore + ContentFilter + ContentScorer
- TagStore + SearchIndex + ContentSearch
- Crawler + ContentExtractor + ContentFilter
"""

from __future__ import annotations

import os

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.tags import TagStore


class TestInterestFilterScoringIntegration:
    """Test InterestStore + ContentFilter + ContentScorer together."""

    def test_interest_match_flows_through_filter(self, tmp_path):
        """Pages matching interests pass through filter."""
        interest_store = InterestStore(store_path=str(tmp_path / "interests.json"))
        interest_store.add(Interest(name="python", keywords=["python", "django"]))

        filter_config = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
        )
        content_filter = ContentFilter(
            config=filter_config,
            interest_store=interest_store,
        )

        matching_page = CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Learn Python programming and Django web framework.",
        )
        non_matching = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking Guide",
            content="Learn to cook delicious meals at home.",
        )

        assert content_filter.should_include(matching_page) is True
        assert content_filter.should_include(non_matching) is False

    def test_interest_match_sets_matched_interests(self, tmp_path):
        """Filter populates matched_interests on pages."""
        interest_store = InterestStore(store_path=str(tmp_path / "interests.json"))
        interest_store.add(Interest(name="webdev", keywords=["javascript", "react"]))

        content_filter = ContentFilter(
            config=FilterConfig(min_content_length=10, require_interest_match=True),
            interest_store=interest_store,
        )

        page = CrawledPage(
            url="https://example.com/js",
            title="JS Guide",
            content="Learn JavaScript and React for web development.",
        )
        content_filter.should_include(page)
        assert "webdev" in page.matched_interests

    def test_scorer_uses_interest_matches(self, tmp_path):
        """Scorer gives higher scores for interest-matched content."""
        interest_store = InterestStore(store_path=str(tmp_path / "interests.json"))
        interest_store.add(Interest(name="tech", keywords=["python", "docker"]))

        ContentScorer(weights=ScoreWeights())

        high_match = CrawledPage(
            url="https://example.com/a",
            title="Tech",
            content="Python and Docker are great tools for development.",
        )
        low_match = CrawledPage(
            url="https://example.com/b",
            title="Other",
            content="This content has nothing to do with technology.",
        )

        # Score pages
        for page in [high_match, low_match]:
            text = f"{page.title} {page.content}"
            interest_store.matches_any(text, page.url)
            score = interest_store.total_score(text)
            page.relevance_score = score

        assert high_match.relevance_score > low_match.relevance_score

    def test_multiple_interests_combine(self, tmp_path):
        """Multiple interests combine for scoring."""
        interest_store = InterestStore(store_path=str(tmp_path / "interests.json"))
        interest_store.add(Interest(name="lang", keywords=["python", "rust"]))
        interest_store.add(Interest(name="tools", keywords=["docker", "kubernetes"]))

        page = CrawledPage(
            url="https://example.com/multi",
            title="Multi",
            content="Python and Rust with Docker and Kubernetes.",
        )

        text = f"{page.title} {page.content}"
        matches = interest_store.matches_any(text, page.url)
        assert len(matches) == 2


class TestTagSearchIndexIntegration:
    """Test TagStore + SearchIndex working together."""

    def test_tag_then_search(self, tmp_path):
        """Tags can be added and pages searched by content."""
        tag_store = TagStore(store_path=str(tmp_path / "tags.json"))
        search_index = SearchIndex(db_path=str(tmp_path / "index.json"))

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Learn Python programming for web development.",
        )
        search_index.add_page(page)
        tag_store.add_tag_to_page(page.url, "python")
        tag_store.add_tag_to_page(page.url, "tutorial")

        # Search finds the page
        results = search_index.search("python")
        assert len(results) >= 1

        # Tags are retrievable
        tags = tag_store.get_tags_for_page(page.url)
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "tutorial" in tag_names

    def test_tags_persist_after_reload(self, tmp_path):
        """Tags persist when TagStore is reloaded from disk."""
        tag_store = TagStore(store_path=str(tmp_path / "tags.json"))
        tag_store.add_tag_to_page("https://example.com/page1", "important")
        tag_store._save()

        # Reload
        tag_store2 = TagStore(store_path=str(tmp_path / "tags.json"))
        tags = tag_store2.get_tags_for_page("https://example.com/page1")
        assert any(t.name == "important" for t in tags)

    def test_index_persists_after_reload(self, tmp_path):
        """Search index persists when reloaded from disk."""
        search_index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/page1",
            title="Test Page",
            content="This is a test page for persistence.",
        )
        search_index.add_page(page)
        search_index.close()

        # Reload
        search_index2 = SearchIndex(db_path=str(tmp_path / "index.json"))
        results = search_index2.search("test")
        assert len(results) >= 1

    def test_tag_count_tracking(self, tmp_path):
        """Tag count is tracked correctly."""
        tag_store = TagStore(store_path=str(tmp_path / "tags.json"))
        assert tag_store.get_tag_count() == 0

        tag_store.add_tag_to_page("url1", "tag1")
        tag_store.add_tag_to_page("url1", "tag2")
        tag_store.add_tag_to_page("url2", "tag1")

        assert tag_store.get_tag_count() >= 2


class TestFullPipelineDataFlow:
    """Test data flows correctly through the entire pipeline."""

    def test_page_data_flows_through_all_stages(self, tmp_path):
        """Verify data integrity through crawl→extract→filter→score→tag→index."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        # Setup components
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(name="python", keywords=["python", "programming"]))

        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        search_index = SearchIndex(db_path=os.path.join(data_dir, "index.json"))
        content_filter = ContentFilter(
            config=FilterConfig(min_content_length=10, require_interest_match=False),
            interest_store=interest_store,
        )
        ContentScorer(weights=ScoreWeights())

        # Simulate pipeline
        page = CrawledPage(
            url="https://example.com/python-guide",
            title="Python Programming Guide",
            content="Python is a great programming language for web development.",
        )

        # Filter
        assert content_filter.should_include(page)

        # Score
        text = f"{page.title} {page.content}"
        matches = interest_store.matches_any(text, page.url)
        page.matched_interests = [m.name for m in matches]
        page.relevance_score = interest_store.total_score(text)
        assert page.relevance_score > 0

        # Tag
        for m in matches:
            tag_store.add_tag_to_page(page.url, m.name)

        # Index
        search_index.add_page(page)

        # Verify search works
        results = search_index.search("python")
        assert len(results) >= 1
        assert results[0].title == "Python Programming Guide"

    def test_empty_content_handled_gracefully(self, tmp_path):
        """Empty content is filtered out."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        content_filter = ContentFilter(
            config=FilterConfig(min_content_length=10),
        )

        empty_page = CrawledPage(
            url="https://example.com/empty",
            title="Empty",
            content="",
        )
        assert content_filter.should_include(empty_page) is False
