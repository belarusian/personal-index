"""Integration tests for the interests workflow.

Tests the full interests workflow: add interests -> crawl -> verify scoring
reflects interests. Uses real module code, not mocked APIs.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from personal_index.content_extractor import ContentExtractor
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline import Pipeline, PipelineConfig
from personal_index.tags import TagStore


class TestInterestsWorkflow:
    """Test the complete interests workflow end-to-end."""

    def setup_method(self):
        """Set up a temporary data directory for each test."""
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmpdir, "interests_data")
        os.makedirs(self.data_dir, exist_ok=True)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_interests_and_verify_scoring(self):
        """Adding interests should affect content scoring.

        Pages matching interests should score higher than non-matching pages.
        """
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        # Add interests
        pipeline.interest_store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
            priority=8,
        ))
        pipeline.interest_store.add(Interest(
            name="cooking",
            keywords=["recipe", "cooking", "baking", "pasta"],
            priority=5,
        ))

        # Verify interests were added
        interests = pipeline.interest_store.list_all()
        assert len(interests) == 2
        interest_names = {i.name for i in interests}
        assert "python" in interest_names
        assert "cooking" in interest_names

        # Score a page matching python interest
        python_page = CrawledPage(
            url="https://example.com/python",
            title="Python Web Frameworks",
            content=(
                "Python is a great language for web development. "
                "Django and Flask are popular Python frameworks. "
                "Python Django Flask Python programming."
            ),
        )

        # Score a page matching cooking interest
        cooking_page = CrawledPage(
            url="https://example.com/cooking",
            title="Italian Cooking",
            content=(
                "Cooking pasta is an art. This recipe for baking "
                "pasta with fresh ingredients is perfect for cooking enthusiasts."
            ),
        )

        # Score a page matching no interests
        unrelated_page = CrawledPage(
            url="https://example.com/unrelated",
            title="Random Topic",
            content=(
                "This content is about something completely unrelated "
                "to our tracked interests. It discusses gardening and "
                "collecting stamps as hobbies."
            ),
        )

        # Score each page
        scorer = ContentScorer(weights=ScoreWeights())
        python_score = scorer.score_page(python_page, pipeline.interest_store)
        cooking_score = scorer.score_page(cooking_page, pipeline.interest_store)
        unrelated_score = scorer.score_page(unrelated_page, pipeline.interest_store)

        # Python page should score higher than unrelated (has keyword matches)
        assert python_score.relevance > unrelated_score.relevance, \
            "Python page should have higher relevance than unrelated page"

        # Cooking page should score higher than unrelated
        assert cooking_score.relevance > unrelated_score.relevance, \
            "Cooking page should have higher relevance than unrelated page"

    def test_interest_priority_affects_scoring(self):
        """Higher priority interests should contribute more to scoring."""
        store = InterestStore(store_path=os.path.join(self.data_dir, "interests.json"))

        # High priority interest
        store.add(Interest(
            name="high_priority",
            keywords=["important"],
            priority=10,
        ))

        # Low priority interest
        store.add(Interest(
            name="low_priority",
            keywords=["important"],
            priority=1,
        ))

        text = "This is an important topic about important things."

        # Total score should reflect both interests
        total = store.total_score(text)
        assert total > 0, "Total score should be positive for matching text"

        # Remove low priority and check score decreases
        store.remove("low_priority")
        total_after = store.total_score(text)
        assert total_after < total, "Score should decrease after removing interest"

    def test_interests_affect_tagging(self):
        """Pages matching interests should be tagged with interest names."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
            tag_by_interest=True,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        pipeline.interest_store.add(Interest(
            name="machine_learning",
            keywords=["machine learning", "neural network", "deep learning"],
            priority=7,
        ))
        pipeline.interest_store.add(Interest(
            name="devops",
            keywords=["docker", "kubernetes", "ci/cd", "deployment"],
            priority=6,
        ))

        # Page matching both interests
        page = CrawledPage(
            url="https://example.com/ml-devops",
            title="ML in DevOps",
            content=(
                "Machine learning models can be deployed using docker and "
                "kubernetes. Deep learning neural network training pipelines "
                "benefit from ci/cd automation for deployment."
            ),
        )

        # Auto-tag the page
        tags = pipeline._auto_tag(page)
        assert "machine_learning" in tags, "Should be tagged with machine_learning"
        assert "devops" in tags, "Should be tagged with devops"

        # Add tags to store
        for tag_name in tags:
            pipeline.tag_store.add_tag_to_page(page.url, tag_name)

        # Verify tags in store
        page_tags = pipeline.tag_store.get_tags_for_page(page.url)
        tag_names = {t.name for t in page_tags}
        assert "machine_learning" in tag_names
        assert "devops" in tag_names

    def test_interest_matching_with_url_patterns(self):
        """Interests with URL patterns should match relevant URLs."""
        store = InterestStore(store_path=os.path.join(self.data_dir, "interests.json"))

        # Use a unique keyword to avoid false matches from text matching
        store.add(Interest(
            name="tech_news",
            keywords=["unique_tech_keyword_12345"],
            url_patterns=["https://techcrunch.com/*"],
            priority=5,
        ))

        # Should match URL pattern (text doesn't contain the unique keyword)
        interest = store.get("tech_news")
        assert interest is not None
        assert interest.matches("Some text", url="https://techcrunch.com/ai-news")

        # Should not match different URL (and text doesn't have the keyword)
        assert not interest.matches("Some other text", url="https://example.com/article")

    def test_disabled_interest_does_not_affect_scoring(self):
        """Disabled interests should not contribute to scoring or tagging."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
            tag_by_interest=True,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        # Add enabled interest
        pipeline.interest_store.add(Interest(
            name="enabled_topic",
            keywords=["python"],
            priority=5,
            enabled=True,
        ))

        # Add disabled interest
        pipeline.interest_store.add(Interest(
            name="disabled_topic",
            keywords=["javascript"],
            priority=5,
            enabled=False,
        ))

        # Page matching both keywords
        page = CrawledPage(
            url="https://example.com/mixed",
            title="Mixed Languages",
            content="Python and javascript are both popular programming languages.",
        )

        # Auto-tag should only include enabled interest
        tags = pipeline._auto_tag(page)
        assert "enabled_topic" in tags, "Enabled interest should tag"
        assert "disabled_topic" not in tags, "Disabled interest should not tag"

    def test_interest_persistence_across_pipeline_reloads(self):
        """Interests should persist to disk and be available after reload."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        # Add interests
        pipeline.interest_store.add(Interest(
            name="persistence_test",
            keywords=["persist", "reload"],
            priority=5,
        ))

        # Verify interests file exists
        interests_path = os.path.join(self.data_dir, "interests.json")
        assert os.path.exists(interests_path), "Interests file should be persisted"

        # Create new pipeline with same data dir
        pipeline2 = Pipeline(data_dir=self.data_dir, config=config)

        # Verify interests were loaded
        interests = pipeline2.interest_store.list_all()
        assert len(interests) >= 1
        assert any(i.name == "persistence_test" for i in interests)

        # Verify scoring still works with loaded interests
        page = CrawledPage(
            url="https://example.com/test",
            title="Test",
            content="This tests persistence and reload functionality.",
        )
        score = pipeline2.scorer.score_page(page, pipeline2.interest_store)
        assert score.relevance > 0, "Loaded interests should affect scoring"

    def test_interests_affect_pipeline_filtering(self):
        """When require_interest_match is True, only matching pages pass filter."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=True,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        pipeline.interest_store.add(Interest(
            name="python",
            keywords=["python", "django"],
            priority=5,
        ))

        # Page matching interest
        matching_page = CrawledPage(
            url="https://example.com/matching",
            title="Python Guide",
            content="Python and Django are great for web development.",
        )

        # Page not matching interest
        non_matching_page = CrawledPage(
            url="https://example.com/nonmatching",
            title="Cooking Guide",
            content="How to make a delicious pasta dish with fresh ingredients.",
        )

        # Matching page should pass
        assert pipeline.add_page_directly(matching_page) is True

        # Non-matching page should be filtered out
        assert pipeline.add_page_directly(non_matching_page) is False

    def test_multiple_interests_combined_scoring(self):
        """Multiple matching interests should combine their scores."""
        store = InterestStore(store_path=os.path.join(self.data_dir, "interests.json"))

        store.add(Interest(
            name="ai",
            keywords=["ai", "artificial intelligence"],
            priority=8,
        ))
        store.add(Interest(
            name="ml",
            keywords=["ml", "machine learning"],
            priority=7,
        ))
        store.add(Interest(
            name="data",
            keywords=["data", "dataset"],
            priority=6,
        ))

        # Text matching all three interests
        text = "AI and machine learning use data from dataset sources. " \
               "Artificial intelligence and ml models process data."

        total_score = store.total_score(text)
        assert total_score > 0, "Combined score should be positive"

        # Verify matches_any finds all three
        matches = store.matches_any(text)
        match_names = {m.name for m in matches}
        assert "ai" in match_names
        assert "ml" in match_names
        assert "data" in match_names

    def test_interest_keywords_case_insensitive(self):
        """Interest keyword matching should be case-insensitive."""
        store = InterestStore(store_path=os.path.join(self.data_dir, "interests.json"))

        store.add(Interest(
            name="case_test",
            keywords=["Python", "Django"],
            priority=5,
        ))

        interest = store.get("case_test")
        assert interest is not None

        # Should match regardless of case
        assert interest.matches("python is great")
        assert interest.matches("PYTHON is great")
        assert interest.matches("Python is great")
        assert interest.matches("django framework")
        assert interest.matches("DJANGO framework")
