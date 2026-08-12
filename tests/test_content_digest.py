"""Tests for content digest module."""

from __future__ import annotations

from personal_index.content_digest import (
    ContentDigest,
    DigestEntry,
    DigestGenerator,
    DigestSection,
)


def make_entry(
    url: str = "https://example.com",
    title: str = "Test",
    summary: str = "Summary",
    tags: list[str] | None = None,
    score: float = 0.0,
    source: str = "",
) -> DigestEntry:
    return DigestEntry(
        url=url,
        title=title,
        summary=summary,
        tags=tags or [],
        score=score,
        source=source,
    )


class TestDigestEntry:
    def test_to_dict(self):
        entry = make_entry(tags=["python"], score=8.0)
        d = entry.to_dict()
        assert d["url"] == "https://example.com"
        assert d["tags"] == ["python"]
        assert d["score"] == 8.0


class TestDigestSection:
    def test_count(self):
        section = DigestSection(
            topic="Python",
            entries=[make_entry(), make_entry()],
        )
        assert section.count == 2


class TestContentDigest:
    def test_to_dict(self):
        digest = ContentDigest(
            title="Daily Digest",
            generated_at="2024-01-15T10:00:00",
            period_start="2024-01-14",
            period_end="2024-01-15",
            sections=[DigestSection(topic="Python", entries=[make_entry()])],
            total_entries=1,
        )
        d = digest.to_dict()
        assert d["title"] == "Daily Digest"
        assert d["total_entries"] == 1
        assert len(d["sections"]) == 1

    def test_format_markdown(self):
        digest = ContentDigest(
            title="Daily Digest",
            generated_at="2024-01-15T10:00:00",
            period_start="2024-01-14",
            period_end="2024-01-15",
            sections=[DigestSection(topic="Python", entries=[make_entry(title="Python Tips")])],
            total_entries=1,
            summary="1 new item",
        )
        md = digest.format_markdown()
        assert "# Daily Digest" in md
        assert "Python Tips" in md
        assert "1 new item" in md

    def test_format_text(self):
        digest = ContentDigest(
            title="Daily Digest",
            generated_at="2024-01-15T10:00:00",
            period_start="2024-01-14",
            period_end="2024-01-15",
            sections=[DigestSection(topic="Python", entries=[make_entry(title="Python Tips")])],
            total_entries=1,
        )
        text = digest.format_text()
        assert "Daily Digest" in text
        assert "Python Tips" in text


class TestDigestGenerator:
    def setup_method(self):
        self.generator = DigestGenerator()
        self.generator.add_entries([
            make_entry(url="https://a.com", title="Python 1", tags=["python"], score=8.0, source="blog"),
            make_entry(url="https://b.com", title="Python 2", tags=["python", "tutorial"], score=7.0, source="blog"),
            make_entry(url="https://c.com", title="JS Guide", tags=["javascript"], score=6.0, source="docs"),
            make_entry(url="https://d.com", title="No Tags", score=5.0, source="blog"),
        ])

    def test_generate_by_tags(self):
        digest = self.generator.generate(group_by="tags")
        assert digest.total_entries == 4
        topics = [s.topic for s in digest.sections]
        assert "python" in topics
        assert "javascript" in topics

    def test_generate_by_source(self):
        digest = self.generator.generate(group_by="source")
        topics = [s.topic for s in digest.sections]
        assert "blog" in topics
        assert "docs" in topics

    def test_generate_no_grouping(self):
        digest = self.generator.generate(group_by="none")
        assert len(digest.sections) == 1
        assert digest.sections[0].topic == "All Content"

    def test_generate_max_entries(self):
        digest = self.generator.generate(group_by="tags", max_entries_per_section=1)
        for section in digest.sections:
            assert section.count <= 1

    def test_generate_summary(self):
        digest = self.generator.generate()
        assert digest.summary
        assert "new items" in digest.summary

    def test_generate_empty(self):
        empty = DigestGenerator()
        digest = empty.generate()
        assert digest.total_entries == 0
        assert "No new content found" in digest.summary

    def test_clear(self):
        self.generator.clear()
        digest = self.generator.generate()
        assert digest.total_entries == 0

    def test_entries_sorted_by_score(self):
        digest = self.generator.generate(group_by="none")
        entries = digest.sections[0].entries
        scores = [e.score for e in entries]
        assert scores == sorted(scores, reverse=True)
