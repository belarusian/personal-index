"""Scoring and filtering integration tests.

These tests verify that content scoring and filtering work correctly
throughout the pipeline, including interest matching and threshold filtering.
"""

from __future__ import annotations

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest


class TestFilterIntegration:
    """Test content filtering with real interest data."""

    def test_filter_allows_matching_content(self, tmp_path):
        """Filter allows content matching interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))

        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Learn Python programming with Django and Flask.",
        )
        assert content_filter.should_include(page) is True

    def test_filter_blocks_non_matching_content(self, tmp_path):
        """Filter blocks content not matching interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python", "django"],
        ))

        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking Recipes",
            content="Delicious recipes for home cooking.",
        )
        assert content_filter.should_include(page) is False

    def test_filter_blocks_short_content(self, tmp_path):
        """Filter blocks content below minimum length."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="test", keywords=["test"]))

        filter_cfg = FilterConfig(
            min_content_length=100,
            require_interest_match=True,
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Too short.",
        )
        assert content_filter.should_include(page) is False

    def test_filter_blocks_blocked_domains(self, tmp_path):
        """Filter blocks content from blocked domains."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="test", keywords=["test"]))

        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
            blocked_domains=["spam.com"],
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://spam.com/page",
            title="Spam Page",
            content="This is test content from a blocked domain.",
        )
        assert content_filter.should_include(page) is False

    def test_filter_gets_reasons(self, tmp_path):
        """Filter provides reasons for exclusion."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))

        filter_cfg = FilterConfig(
            min_content_length=100,
            require_interest_match=True,
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/short",
            title="X",
            content="Short.",
        )
        reasons = content_filter.get_filter_reasons(page)
        assert len(reasons) > 0
        any_length_reason = any("content length" in r for r in reasons)
        any_title_reason = any("title too short" in r for r in reasons)
        assert any_length_reason or any_title_reason

    def test_filter_passes_without_interests(self, tmp_path):
        """Filter passes all content when require_interest_match=False."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        # No interests added

        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=False,
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/anything",
            title="Any Content",
            content="This content has no matching interests.",
        )
        assert content_filter.should_include(page) is True

    def test_filter_blocks_patterns(self, tmp_path):
        """Filter blocks content matching blocked patterns."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="test", keywords=["test"]))

        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
            blocked_patterns=["spam", "advertising"],
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="This is test content with spam in it.",
        )
        assert content_filter.should_include(page) is False

    def test_filter_min_relevance_score(self, tmp_path):
        """Filter enforces minimum relevance score."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))

        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
            min_relevance_score=10.0,
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="python",  # Only one match, low score
        )
        reasons = content_filter.get_filter_reasons(page)
        any_score_reason = any("relevance score" in r for r in reasons)
        assert any_score_reason


class TestScorerIntegration:
    """Test content scoring with real data."""

    def test_scorer_basic_scoring(self):
        """Scorer produces valid scores."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=5,
            total_keywords=10,
            word_count=500,
            domain_authority=0.8,
        )
        assert 0 <= result.total <= 1.0
        assert 0 <= result.relevance <= 1.0
        assert 0 <= result.quality <= 1.0

    def test_scorer_high_keyword_match(self):
        """Scorer gives high relevance score for many keyword matches."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=10,
            total_keywords=10,
            word_count=1000,
            domain_authority=0.9,
        )
        assert result.relevance == 1.0

    def test_scorer_no_keyword_match(self):
        """Scorer gives zero relevance score for no matches."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=0,
            total_keywords=10,
            word_count=500,
            domain_authority=0.5,
        )
        assert result.relevance == 0.0

    def test_scorer_custom_weights(self):
        """Scorer respects custom weight configuration."""
        weights = ScoreWeights(
            relevance=0.5,
            quality=0.3,
            authority=0.2,
        )
        scorer = ContentScorer(weights=weights)
        result = scorer.score(
            keyword_matches=5,
            total_keywords=10,
            word_count=500,
            domain_authority=0.8,
        )
        assert 0 <= result.total <= 1.0

    def test_scorer_page_scoring_with_interests(self, tmp_path):
        """Scorer scores pages against interest store."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))

        scorer = ContentScorer()
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Python Django Flask Python Django Flask Python.",
        )
        result = scorer.score_page(page, interest_store=store)
        assert result.relevance > 0

    def test_scorer_page_scoring_no_interests(self, tmp_path):
        """Scorer handles pages with no interest matches."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))

        scorer = ContentScorer()
        page = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking",
            content="Recipes and cooking tips.",
        )
        result = scorer.score_page(page, interest_store=store)
        assert result.relevance == 0.0

    def test_scorer_ranking(self):
        """Scorer ranks items correctly."""
        scorer = ContentScorer()
        items = [
            {"keyword_matches": 10, "total_keywords": 10, "word_count": 1000, "domain_authority": 0.9},
            {"keyword_matches": 0, "total_keywords": 10, "word_count": 100, "domain_authority": 0.1},
            {"keyword_matches": 5, "total_keywords": 10, "word_count": 500, "domain_authority": 0.5},
        ]
        ranked = scorer.rank(items, limit=3)
        assert len(ranked) == 3
        # Best item should be first
        assert ranked[0][0]["keyword_matches"] == 10
        # Worst item should be last
        assert ranked[2][0]["keyword_matches"] == 0

    def test_scorer_ranking_limit(self):
        """Scorer ranking respects limit."""
        scorer = ContentScorer()
        items = [
            {"keyword_matches": i, "total_keywords": 10, "word_count": 500, "domain_authority": 0.5}
            for i in range(20)
        ]
        ranked = scorer.rank(items, limit=5)
        assert len(ranked) == 5


class TestFilterAndScorerCombined:
    """Test filter and scorer working together."""

    def test_filter_then_score_workflow(self, tmp_path):
        """Filter then score workflow produces correct results."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))

        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
        )
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)
        scorer = ContentScorer()

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Python Django Flask Python Django Flask.",
            ),
            CrawledPage(
                url="https://example.com/cooking",
                title="Cooking",
                content="Recipes and cooking tips.",
            ),
            CrawledPage(
                url="https://example.com/short",
                title="X",
                content="Hi",
            ),
        ]

        # Filter
        included = [p for p in pages if content_filter.should_include(p)]
        assert len(included) == 1
        assert included[0].url == "https://example.com/python"

        # Score
        for page in included:
            score = scorer.score_page(page, interest_store=store)
            assert score.relevance > 0
