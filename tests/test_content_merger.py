"""Tests for the content merger module."""

from datetime import datetime

from personal_index.content_merger import ContentMerger, MergeResult


class TestMergeResult:
    def test_to_dict(self) -> None:
        result = MergeResult(
            total_input=100,
            merged_count=80,
            duplicates_removed=20,
            conflicts_resolved=5,
        )
        d = result.to_dict()
        assert d["total_input"] == 100
        assert d["duplicates_removed"] == 20


class TestContentMerger:
    def setup_method(self) -> None:
        self.merger = ContentMerger(dedup_key="url")

    def test_merge_no_duplicates(self) -> None:
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "title": "A1"},
            ],
            "source2": [
                {"id": "2", "url": "https://b.com/2", "title": "B2"},
            ],
        }
        items, result = self.merger.merge(sources)
        assert len(items) == 2
        assert result.duplicates_removed == 0

    def test_merge_duplicates(self) -> None:
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "title": "A1"},
            ],
            "source2": [
                {"id": "1", "url": "https://a.com/1", "title": "A1 Updated"},
            ],
        }
        items, result = self.merger.merge(sources)
        assert len(items) == 1
        assert result.duplicates_removed == 1
        assert result.conflicts_resolved == 1

    def test_merge_conflict_newest(self) -> None:
        self.merger = ContentMerger(dedup_key="url", conflict_strategy="newest")
        sources = {
            "source1": [
                {
                    "id": "1",
                    "url": "https://a.com/1",
                    "title": "Old",
                    "published_at": datetime(2024, 1, 1),
                },
            ],
            "source2": [
                {
                    "id": "1",
                    "url": "https://a.com/1",
                    "title": "New",
                    "published_at": datetime(2024, 1, 2),
                },
            ],
        }
        items, _ = self.merger.merge(sources)
        assert items[0]["title"] == "New"

    def test_merge_conflict_highest_score(self) -> None:
        self.merger = ContentMerger(
            dedup_key="url", conflict_strategy="highest_score",
        )
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "score": 0.5},
            ],
            "source2": [
                {"id": "1", "url": "https://a.com/1", "score": 0.9},
            ],
        }
        items, _ = self.merger.merge(sources)
        assert items[0]["score"] == 0.9

    def test_merge_conflict_merge_tags(self) -> None:
        self.merger = ContentMerger(
            dedup_key="url", conflict_strategy="merge_tags",
        )
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "tags": ["python"]},
            ],
            "source2": [
                {"id": "1", "url": "https://a.com/1", "tags": ["web"]},
            ],
        }
        items, _ = self.merger.merge(sources)
        tags = set(items[0]["tags"])
        assert "python" in tags
        assert "web" in tags

    def test_merge_with_priority(self) -> None:
        sources = {
            "low": [
                {"id": "1", "url": "https://a.com/1", "title": "Low"},
            ],
            "high": [
                {"id": "1", "url": "https://a.com/1", "title": "High"},
            ],
        }
        items, _ = self.merger.merge_with_priority(
            sources, priority_order=["high", "low"],
        )
        assert items[0]["title"] == "High"

    def test_merge_tags_dedup(self) -> None:
        items = [
            {"id": "1", "tags": ["python", "python", "web", "web"]},
        ]
        result = self.merger.merge_tags(items)
        assert len(result[0]["tags"]) == 2

    def test_merge_empty_sources(self) -> None:
        items, result = self.merger.merge({})
        assert len(items) == 0
        assert result.total_input == 0

    def test_merge_missing_dedup_key(self) -> None:
        sources = {
            "source1": [
                {"id": "1", "title": "No URL"},
            ],
        }
        items, result = self.merger.merge(sources)
        assert len(items) == 1
