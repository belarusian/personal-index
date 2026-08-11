"""Tests for the content digest module."""

from datetime import datetime, timedelta

from personal_index.content_digest import (
    ContentDigest,
    DigestConfig,
    DigestFrequency,
    DigestGenerator,
    DigestItem,
)


class TestDigestConfig:
    def test_defaults(self) -> None:
        config = DigestConfig()
        assert config.frequency == DigestFrequency.DAILY
        assert config.max_items == 20
        assert config.min_score == 0.0
        assert config.include_tags is True


class TestDigestItem:
    def test_create(self) -> None:
        item = DigestItem(
            title="Test",
            url="https://example.com/test",
            tags=["python"],
            score=0.8,
        )
        assert item.title == "Test"
        assert item.tags == ["python"]


class TestContentDigest:
    def test_to_dict(self) -> None:
        digest = ContentDigest(
            title="Test Digest",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 2),
            items=[
                DigestItem(title="Item 1", url="https://example.com/1"),
            ],
            total_new=1,
            top_tags=["python"],
            top_domains=["example.com"],
        )
        d = digest.to_dict()
        assert d["title"] == "Test Digest"
        assert len(d["items"]) == 1
        assert d["total_new"] == 1


class TestDigestGenerator:
    def setup_method(self) -> None:
        self.now = datetime(2024, 1, 15, 12, 0)
        self.items = [
            {
                "title": "Article 1",
                "url": "https://example.com/1",
                "description": "First article description.",
                "tags": ["python", "web"],
                "score": 0.9,
                "published_at": datetime(2024, 1, 14),
            },
            {
                "title": "Article 2",
                "url": "https://example.com/2",
                "description": "Second article description.",
                "tags": ["javascript"],
                "score": 0.7,
                "published_at": datetime(2024, 1, 13),
            },
            {
                "title": "Article 3",
                "url": "https://other.com/3",
                "description": "Third article.",
                "tags": ["python", "data"],
                "score": 0.5,
                "published_at": datetime(2024, 1, 14),
            },
            {
                "title": "Low Score",
                "url": "https://example.com/low",
                "tags": ["spam"],
                "score": 0.1,
                "published_at": datetime(2024, 1, 14),
            },
        ]

    def test_generate_basic(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert digest.title
        assert len(digest.items) > 0

    def test_generate_min_score_filter(self) -> None:
        config = DigestConfig(min_score=0.6)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert item.score >= 0.6

    def test_generate_max_items(self) -> None:
        config = DigestConfig(max_items=1)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert len(digest.items) <= 1

    def test_generate_sort_by_score(self) -> None:
        config = DigestConfig(sort_by="score")
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        scores = [i.score for i in digest.items]
        assert scores == sorted(scores, reverse=True)

    def test_generate_top_tags(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert "python" in digest.top_tags

    def test_generate_top_domains(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert "example.com" in digest.top_domains

    def test_generate_no_preview(self) -> None:
        config = DigestConfig(include_preview=False)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert item.preview == ""

    def test_generate_no_tags(self) -> None:
        config = DigestConfig(include_tags=False)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert item.tags == []

    def test_generate_empty_items(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate([])
        assert len(digest.items) == 0
        assert digest.total_new == 0

    def test_generate_title(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 14),
            period_end=datetime(2024, 1, 15),
        )
        assert "Daily Digest" in digest.title

    def test_generate_weekly_title(self) -> None:
        config = DigestConfig(frequency=DigestFrequency.WEEKLY)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 8),
            period_end=datetime(2024, 1, 15),
        )
        assert "Weekly Digest" in digest.title

    def test_preview_truncation(self) -> None:
        config = DigestConfig(preview_length=10)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert len(item.preview) <= 10
