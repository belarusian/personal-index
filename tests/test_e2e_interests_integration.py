"""Interest management integration tests.

These tests verify interest matching, scoring, and integration with
the filter and pipeline components.
"""

from __future__ import annotations

from unittest.mock import patch

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner


class TestInterestMatching:
    """Test interest matching logic."""

    def test_interest_matches_keyword(self):
        """Interest matches when keyword is in text."""
        interest = Interest(
            name="python",
            keywords=["python", "django"],
        )
        assert interest.matches("Learn Python programming") is True
        assert interest.matches("Django web framework") is True
        assert interest.matches("Cooking recipes") is False

    def test_interest_matches_value_field(self):
        """Interest matches when value field is in text."""
        interest = Interest(
            name="rust",
            value="rust",
        )
        assert interest.matches("Rust programming language") is True
        assert interest.matches("Cooking recipes") is False

    def test_interest_disabled_no_match(self):
        """Disabled interest never matches."""
        interest = Interest(
            name="python",
            keywords=["python"],
            enabled=False,
        )
        assert interest.matches("Python programming") is False

    def test_interest_score_calculation(self):
        """Interest score reflects keyword frequency."""
        interest = Interest(
            name="python",
            keywords=["python"],
            priority=5,
        )
        score1 = interest.score("python python python")
        score2 = interest.score("python")
        assert score1 > score2

    def test_interest_score_disabled(self):
        """Disabled interest returns zero score."""
        interest = Interest(
            name="python",
            keywords=["python"],
            enabled=False,
        )
        assert interest.score("python python") == 0.0


class TestInterestStoreIntegration:
    """Test InterestStore operations."""

    def test_store_add_and_list(self, tmp_path):
        """Can add and list interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="webdev", keywords=["javascript", "react"]))

        interests = store.list_all()
        assert len(interests) == 2
        names = {i.name for i in interests}
        assert names == {"python", "webdev"}

    def test_store_remove(self, tmp_path):
        """Can remove interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="temp", keywords=["temp"]))

        assert store.remove("temp") is True
        assert store.remove("nonexistent") is False
        assert len(store.list_all()) == 1

    def test_store_toggle(self, tmp_path):
        """Can toggle interest enabled status."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], enabled=True))

        interest = store.toggle("python")
        assert interest is not None
        assert interest.enabled is False

        interest = store.toggle("python")
        assert interest.enabled is True

    def test_store_matches_any(self, tmp_path):
        """Can find all matching interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="webdev", keywords=["javascript"]))
        store.add(Interest(name="cooking", keywords=["recipes"]))

        matches = store.matches_any("Python and javascript programming")
        names = {m.name for m in matches}
        assert names == {"python", "webdev"}

    def test_store_total_score(self, tmp_path):
        """Can calculate total score across interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))
        store.add(Interest(name="webdev", keywords=["javascript"], priority=3))

        score = store.total_score("python python javascript")
        assert score > 0

    def test_store_get_all_keywords(self, tmp_path):
        """Can get all keywords from all interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django"]))
        store.add(Interest(name="webdev", keywords=["javascript", "react"]))

        keywords = store.get_all_keywords()
        assert keywords == {"python", "django", "javascript", "react"}

    def test_store_persistence(self, tmp_path):
        """Interests persist to disk."""
        path = str(tmp_path / "interests.json")
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="python", keywords=["python", "django"]))

        store2 = InterestStore(store_path=path)
        interests = store2.list_all()
        assert len(interests) == 1
        assert interests[0].name == "python"
        assert "python" in interests[0].keywords

    def test_store_update_priority(self, tmp_path):
        """Can update interest priority."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=3))

        interest = store.update_priority("python", 8)
        assert interest is not None
        assert interest.priority == 8

    def test_store_priority_clamped(self, tmp_path):
        """Priority is clamped to 1-10 range."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))

        store.update_priority("python", 0)
        assert store.get("python").priority == 1

        store.update_priority("python", 15)
        assert store.get("python").priority == 10


class TestInterestPipelineIntegration:
    """Test interests within the pipeline."""

    def test_pipeline_uses_interests_for_filtering(self, tmp_path):
        """Pipeline filters based on interest matches."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming tutorial.",
            ),
            CrawledPage(
                url="https://example.com/cooking",
                title="Cooking",
                content="Recipes and cooking tips.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        # At least one page should be filtered in
        assert stats.pages_filtered_in >= 1
        assert stats.pages_indexed >= 1
        runner.close()

    def test_pipeline_interests_matched_count(self, tmp_path):
        """Pipeline tracks interests matched."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming tutorial.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.interests_matched >= 1
        runner.close()

    def test_pipeline_disabled_interests_ignored(self, tmp_path):
        """Pipeline ignores disabled interests."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
            enabled=False,
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming tutorial.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        # Page should still be indexed (require_interest_match=False by default in pipeline)
        assert stats.pages_indexed == 1
        runner.close()
