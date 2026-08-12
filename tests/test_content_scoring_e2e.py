"""End-to-end tests for content scoring pipeline."""

from __future__ import annotations

from personal_index.content_scoring import ContentScore, ContentScorer


class TestContentScoringE2E:
    """Test content scoring with realistic scenarios."""

    def test_scorer_high_keyword_match(self):
        """Pages with many keyword matches get high scores."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=10,
            total_keywords=10,
            word_count=500,
            domain_authority=0.9,
        )
        assert result.total > 0.5

    def test_scorer_no_keyword_match(self):
        """Pages with no keyword matches get low scores."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=0,
            total_keywords=10,
            word_count=500,
            domain_authority=0.5,
        )
        assert result.total < 0.5

    def test_scorer_long_content_bonus(self):
        """Longer content gets a slight bonus."""
        scorer = ContentScorer()
        short = scorer.score(
            keyword_matches=5, total_keywords=10,
            word_count=50, domain_authority=0.5,
        )
        long = scorer.score(
            keyword_matches=5, total_keywords=10,
            word_count=2000, domain_authority=0.5,
        )
        assert long.total >= short.total

    def test_scorer_domain_authority_impact(self):
        """Higher domain authority increases score."""
        scorer = ContentScorer()
        low_auth = scorer.score(
            keyword_matches=5, total_keywords=10,
            word_count=500, domain_authority=0.1,
        )
        high_auth = scorer.score(
            keyword_matches=5, total_keywords=10,
            word_count=500, domain_authority=1.0,
        )
        assert high_auth.total >= low_auth.total

    def test_scorer_result_components(self):
        """ContentScore has all expected components."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=5, total_keywords=10,
            word_count=500, domain_authority=0.5,
        )
        assert hasattr(result, "relevance")
        assert hasattr(result, "quality")
        assert hasattr(result, "total")
        assert isinstance(result, ContentScore)

    def test_scorer_zero_total_keywords(self):
        """Handle edge case of zero total keywords."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=0, total_keywords=0,
            word_count=100, domain_authority=0.5,
        )
        assert result.total >= 0

    def test_scorer_ranking(self):
        """Test ranking multiple items."""
        scorer = ContentScorer()
        items = [
            {"keyword_matches": 8, "total_keywords": 10, "word_count": 1000, "domain_authority": 0.9},
            {"keyword_matches": 2, "total_keywords": 10, "word_count": 200, "domain_authority": 0.3},
            {"keyword_matches": 5, "total_keywords": 10, "word_count": 500, "domain_authority": 0.7},
        ]
        ranked = scorer.rank(items, limit=2)
        assert len(ranked) == 2
        # First item should rank highest
        assert ranked[0][1].total >= ranked[1][1].total

    def test_scorer_to_dict(self):
        """ContentScore can be serialized to dict."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=5, total_keywords=10,
            word_count=500, domain_authority=0.5,
        )
        d = result.to_dict()
        assert "total" in d
        assert "relevance" in d
        assert "factors" in d
