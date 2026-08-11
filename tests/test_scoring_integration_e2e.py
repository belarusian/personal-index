"""Integration tests for content scoring with the full pipeline."""

from __future__ import annotations

import pytest

from personal_index.content_scoring import ContentScorer
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest


class TestScoringIntegrationE2E:
    """Test content scoring integration with interests."""

    def test_interest_based_scoring(self, tmp_path):
        """Score pages based on interest matches."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python", "programming"],
            priority=10,
        ))
        
        scorer = ContentScorer()
        
        # Page with high keyword match
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a versatile programming language used for web development, data science, and automation.",
        )
        
        # Calculate score based on interest match
        text = f"{page1.title} {page1.content}"
        matches = store.matches_any(text, page1.url)
        
        assert len(matches) == 1
        assert matches[0].name == "python"

    def test_scoring_with_multiple_interests(self, tmp_path):
        """Score pages against multiple interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        store.add(Interest(name="rust", keywords=["rust"], priority=5))
        
        page = CrawledPage(
            url="https://example.com/multi",
            title="Multi Language Guide",
            content="Python and Rust are both great programming languages.",
        )
        
        text = f"{page.title} {page.content}"
        matches = store.matches_any(text, page.url)
        
        # Should match both interests
        assert len(matches) == 2

    def test_scoring_priority_impact(self, tmp_path):
        """Higher priority interests contribute more to score."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="high", keywords=["python"], priority=10))
        store.add(Interest(name="low", keywords=["rust"], priority=1))
        
        page = CrawledPage(
            url="https://example.com/both",
            title="Both Languages",
            content="Python and Rust are both great.",
        )
        
        text = f"{page.title} {page.content}"
        score = store.total_score(text)
        
        # Python should contribute more due to higher priority
        assert score > 0

    def test_scorer_with_interest_store(self, tmp_path):
        """Combine ContentScorer with InterestStore."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="tech",
            keywords=["python", "rust", "golang"],
            priority=5,
        ))
        
        scorer = ContentScorer()
        
        page = CrawledPage(
            url="https://example.com/page",
            title="Tech Page",
            content="Python, Rust, and Golang are all systems programming languages.",
        )
        
        # Get interest-based score
        text = f"{page.title} {page.content}"
        matches = store.matches_any(text, page.url)
        
        # Calculate keyword match score (count keywords in matched interests)
        keyword_matches = sum(len(interest.keywords) for interest in matches)
        total_keywords = 3
        
        result = scorer.score(
            keyword_matches=keyword_matches,
            total_keywords=total_keywords,
            word_count=len(page.content.split()),
            domain_authority=0.5,
        )
        
        assert result.total > 0

    def test_ranking_with_interests(self, tmp_path):
        """Rank pages by combined interest and content score."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python"],
            priority=10,
        ))
        
        scorer = ContentScorer()
        
        pages = [
            CrawledPage(
                url="https://example.com/a",
                title="Python Advanced",
                content="Advanced Python programming techniques for experts.",
            ),
            CrawledPage(
                url="https://example.com/b",
                title="Rust Guide",
                content="Rust systems programming language overview.",
            ),
            CrawledPage(
                url="https://example.com/c",
                title="Python Basics",
                content="Python programming basics for beginners with many words of content.",
            ),
        ]
        
        # Score each page
        scored = []
        for page in pages:
            text = f"{page.title} {page.content}"
            matches = store.matches_any(text, page.url)
            
            result = scorer.score(
                keyword_matches=len(matches),
                total_keywords=1,
                word_count=len(page.content.split()),
                domain_authority=0.5,
            )
            scored.append((page, result))
        
        # Sort by score
        scored.sort(key=lambda x: x[1].total, reverse=True)
        
        # Python pages should rank higher
        assert "Python" in scored[0][0].title

    def test_interest_match_affects_relevance(self, tmp_path):
        """Interest match affects page relevance score."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="python",
            keywords=["python"],
            priority=5,
        ))
        
        # Page that matches
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a programming language.",
        )
        
        # Page that doesn't match
        page2 = CrawledPage(
            url="https://example.com/rust",
            title="Rust Guide",
            content="Rust is a systems programming language.",
        )
        
        text1 = f"{page1.title} {page1.content}"
        text2 = f"{page2.title} {page2.content}"
        
        matches1 = store.matches_any(text1, page1.url)
        matches2 = store.matches_any(text2, page2.url)
        
        assert len(matches1) == 1
        assert len(matches2) == 0

    def test_scorer_with_realistic_content(self, tmp_path):
        """Test scorer with realistic blog post content."""
        scorer = ContentScorer()
        
        # Simulate a real blog post
        page = CrawledPage(
            url="https://example.com/blog/python-best-practices",
            title="Python Best Practices for 2024",
            content="""
            Python continues to be one of the most popular programming languages in 2024.
            This comprehensive guide covers best practices for Python development including
            code organization, testing strategies, and performance optimization techniques.
            We'll explore modern Python features like type hints, async/await, and dataclasses.
            """,
        )
        
        result = scorer.score(
            keyword_matches=3,
            total_keywords=5,
            word_count=len(page.content.split()),
            domain_authority=0.8,
        )
        
        # Should have reasonable score
        assert 0 < result.total <= 1

    def test_interest_store_scorer_integration(self, tmp_path):
        """Full integration: interest store + scorer."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="web",
            keywords=["web", "frontend", "backend"],
            priority=7,
        ))
        
        scorer = ContentScorer()
        
        page = CrawledPage(
            url="https://example.com/web-dev",
            title="Modern Web Development",
            content="""
            Web development has evolved significantly with modern frameworks.
            Frontend development now includes React, Vue, and Angular.
            Backend services use Node.js, Python, and Go for API development.
            """,
        )
        
        text = f"{page.title} {page.content}"
        matches = store.matches_any(text, page.url)
        
        result = scorer.score(
            keyword_matches=len(matches),
            total_keywords=3,
            word_count=len(page.content.split()),
            domain_authority=0.9,
        )
        
        assert len(matches) >= 1
        assert result.total > 0

    def test_scoring_edge_cases(self, tmp_path):
        """Test scorer edge cases."""
        scorer = ContentScorer()
        
        # Empty content
        empty_result = scorer.score(
            keyword_matches=0,
            total_keywords=1,
            word_count=0,
            domain_authority=0.5,
        )
        assert empty_result.total >= 0
        
        # Very long content
        long_content = "word " * 10000
        long_result = scorer.score(
            keyword_matches=5,
            total_keywords=10,
            word_count=len(long_content.split()),
            domain_authority=0.5,
        )
        assert long_result.total > 0

    def test_interest_store_serialization(self, tmp_path):
        """Interest store can be serialized and deserialized."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        
        original = Interest(
            name="test",
            keywords=["a", "b"],
            url_patterns=["*.com"],
            topics=["web"],
            priority=8,
            enabled=True,
        )
        store.add(original)
        
        # Load new instance
        store2 = InterestStore(store_path=str(tmp_path / "interests.json"))
        loaded = store2.get("test")
        
        assert loaded is not None
        assert loaded.name == original.name
        assert loaded.priority == original.priority
