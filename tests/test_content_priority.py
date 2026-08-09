"""Tests for content_priority module - score content importance."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_priority import (
    ContentPriority,
    PriorityConfig,
    PriorityScore,
    PriorityLevel,
    PriorityScorer,
)


class TestPriorityConfig:
    """Test PriorityConfig dataclass."""

    def test_default_config(self):
        config = PriorityConfig()
        assert config.relevance_weight == 0.3
        assert config.freshness_weight == 0.2
        assert config.authority_weight == 0.2
        assert config.engagement_weight == 0.15
        assert config.topical_weight == 0.15

    def test_custom_weights(self):
        config = PriorityConfig(
            relevance_weight=0.5,
            freshness_weight=0.1,
        )
        assert config.relevance_weight == 0.5
        assert config.freshness_weight == 0.1

    def test_weights_sum(self):
        config = PriorityConfig()
        total = (
            config.relevance_weight
            + config.freshness_weight
            + config.authority_weight
            + config.engagement_weight
            + config.topical_weight
        )
        assert abs(total - 1.0) < 0.01


class TestPriorityLevel:
    """Test PriorityLevel enum."""

    def test_all_levels(self):
        levels = list(PriorityLevel)
        assert PriorityLevel.CRITICAL in levels
        assert PriorityLevel.HIGH in levels
        assert PriorityLevel.MEDIUM in levels
        assert PriorityLevel.LOW in levels

    def test_level_ordering(self):
        assert PriorityLevel.CRITICAL > PriorityLevel.HIGH
        assert PriorityLevel.HIGH > PriorityLevel.MEDIUM
        assert PriorityLevel.MEDIUM > PriorityLevel.LOW

    def test_from_score(self):
        assert PriorityLevel.from_score(0.9) == PriorityLevel.CRITICAL
        assert PriorityLevel.from_score(0.7) == PriorityLevel.HIGH
        assert PriorityLevel.from_score(0.4) == PriorityLevel.MEDIUM
        assert PriorityLevel.from_score(0.1) == PriorityLevel.LOW


class TestPriorityScore:
    """Test PriorityScore dataclass."""

    def test_create_score(self):
        score = PriorityScore(
            total=0.75,
            relevance=0.9,
            freshness=0.8,
            authority=0.85,
            engagement=0.8,
            topical=0.9,
        )
        assert score.total == 0.75
        assert score.level == PriorityLevel.HIGH

    def test_score_level_mapping(self):
        high = PriorityScore(total=0.9, relevance=0.9, freshness=0.9,
                            authority=0.9, engagement=0.9, topical=0.9)
        assert high.level == PriorityLevel.CRITICAL

        low = PriorityScore(total=0.1, relevance=0.1, freshness=0.1,
                           authority=0.1, engagement=0.1, topical=0.1)
        assert low.level == PriorityLevel.LOW


class TestContentPriority:
    """Test ContentPriority dataclass."""

    def test_create_priority(self):
        priority = ContentPriority(
            url="https://example.com",
            title="Important Article",
            score=PriorityScore(
                total=0.8, relevance=0.8, freshness=0.8,
                authority=0.8, engagement=0.8, topical=0.8,
            ),
        )
        assert priority.url == "https://example.com"
        assert priority.score.total == 0.8

    def test_priority_comparison(self):
        s1 = PriorityScore(total=0.9, relevance=0.9, freshness=0.9,
                          authority=0.9, engagement=0.9, topical=0.9)
        s2 = PriorityScore(total=0.5, relevance=0.5, freshness=0.5,
                          authority=0.5, engagement=0.5, topical=0.5)
        p1 = ContentPriority(url="a", title="A", score=s1)
        p2 = ContentPriority(url="b", title="B", score=s2)
        assert p1 > p2


class TestPriorityScorerRelevance:
    """Test relevance scoring."""

    def test_keyword_match_boosts_relevance(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "Python Programming",
            "content": "Python is a great programming language",
            "keywords": ["python", "programming"],
        }
        score = scorer.score(content)
        assert score.relevance > 0

    def test_no_keywords_low_relevance(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "Random",
            "content": "Some random text here",
            "keywords": [],
        }
        score = scorer.score(content)
        assert score.relevance < 0.5


class TestPriorityScorerFreshness:
    """Test freshness scoring."""

    def test_recent_content_high_freshness(self):
        scorer = PriorityScorer()
        now = datetime.now(timezone.utc)
        content = {
            "url": "https://example.com",
            "title": "Recent",
            "content": "Fresh content",
            "published_date": now.isoformat(),
        }
        score = scorer.score(content)
        assert score.freshness > 0.8

    def test_old_content_low_freshness(self):
        scorer = PriorityScorer()
        old = datetime.now(timezone.utc) - timedelta(days=365)
        content = {
            "url": "https://example.com",
            "title": "Old",
            "content": "Old content",
            "published_date": old.isoformat(),
        }
        score = scorer.score(content)
        assert score.freshness < 0.5

    def test_no_date_default_freshness(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "No Date",
            "content": "Content without date",
        }
        score = scorer.score(content)
        assert 0.0 <= score.freshness <= 1.0


class TestPriorityScorerAuthority:
    """Test authority scoring."""

    def test_high_authority_domain(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "Article",
            "content": "Content here",
            "domain_authority": 90,
        }
        score = scorer.score(content)
        assert score.authority > 0.7

    def test_low_authority_domain(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "Article",
            "content": "Content here",
            "domain_authority": 10,
        }
        score = scorer.score(content)
        assert score.authority < 0.3


class TestPriorityScorerEngagement:
    """Test engagement scoring."""

    def test_high_engagement(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "Popular",
            "content": "Content here",
            "views": 10000,
            "likes": 500,
            "shares": 100,
        }
        score = scorer.score(content)
        assert score.engagement > 0.5

    def test_no_engagement_data(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "Unknown",
            "content": "Content here",
        }
        score = scorer.score(content)
        assert score.engagement >= 0.0


class TestPriorityScorerTopical:
    """Test topical relevance scoring."""

    def test_matching_topics_boost_score(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "AI News",
            "content": "Artificial intelligence news",
            "tags": ["ai", "technology"],
            "user_interests": ["ai", "technology", "science"],
        }
        score = scorer.score(content)
        assert score.topical > 0.5

    def test_no_matching_topics(self):
        scorer = PriorityScorer()
        content = {
            "url": "https://example.com",
            "title": "Cooking",
            "content": "Recipe for pasta",
            "tags": ["cooking", "food"],
            "user_interests": ["ai", "technology"],
        }
        score = scorer.score(content)
        assert score.topical < 0.5


class TestPriorityScorerIntegration:
    """Integration tests for priority scoring."""

    def test_score_multiple_items(self):
        scorer = PriorityScorer()
        items = [
            {"url": "https://a.com", "title": "A", "content": "First article content", "keywords": ["test"]},
            {"url": "https://b.com", "title": "B", "content": "Second article content", "keywords": ["test"]},
        ]
        results = scorer.score_batch(items)
        assert len(results) == 2

    def test_rank_items(self):
        scorer = PriorityScorer()
        items = [
            {"url": "https://a.com", "title": "A", "content": "Important content about technology and innovation",
             "keywords": ["technology"], "domain_authority": 90,
             "views": 1000, "likes": 100, "tags": ["tech"],
             "user_interests": ["technology"]},
            {"url": "https://b.com", "title": "B", "content": "Less relevant content about something else",
             "keywords": [], "domain_authority": 10,
             "tags": [], "user_interests": ["technology"]},
        ]
        ranked = scorer.rank(items)
        assert len(ranked) == 2
        assert ranked[0].score.total >= ranked[1].score.total

    def test_empty_content(self):
        scorer = PriorityScorer()
        content = {"url": "https://empty.com", "title": "", "content": ""}
        score = scorer.score(content)
        assert score.total >= 0.0
        assert score.total <= 1.0

    def test_custom_weights_affect_score(self):
        config = PriorityConfig(freshness_weight=0.5, relevance_weight=0.05)
        scorer = PriorityScorer(config=config)
        now = datetime.now(timezone.utc)
        content = {
            "url": "https://example.com",
            "title": "Fresh",
            "content": "Very fresh content here",
            "published_date": now.isoformat(),
        }
        score = scorer.score(content)
        # Freshness should dominate with 0.5 weight
        assert score.freshness > 0.8
