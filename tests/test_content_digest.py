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


class TestModuleDocstringContract:
    def test_docstring_does_not_promise_interests_grouping(self):
        """Regression: module docstring must not over-promise capabilities.

        The module implements no interest-based grouping (only tags and
        source), so its docstring must not claim to group by 'interests'
        (TICKET-326).
        """
        import personal_index.content_digest as cd

        doc = (cd.__doc__ or "").lower()
        assert "interest" not in doc


class TestGenerateDocstringClaim:
    def test_generate_caps_each_section_at_default_limit(self):
        """Pin the corrected docstring claim: each section is capped at
        max_entries_per_section (default 10) entries in the returned digest."""
        gen = DigestGenerator()
        # 15 entries all sharing one tag -> one section that must be capped at 10
        for i in range(15):
            gen.add_entry(make_entry(title=f"E{i}", tags=["python"], score=float(i)))
        digest = gen.generate()
        # The single "python" section must hold exactly the default cap of 10
        python_section = next(s for s in digest.sections if s.topic == "python")
        assert python_section.count == 10
        # And the kept entries are the 10 highest-scored (score desc sort)
        assert [e.score for e in python_section.entries] == [
            float(i) for i in range(14, 4, -1)
        ]


class TestGeneratorDocstringClaim:
    def test_digest_contains_exactly_added_entries(self):
        """Pin the corrected class docstring claim: the digest is built
        from the entries added via add_entry/add_entries (no external or
        indexed source), and source-grouping produces one section per source."""
        gen = DigestGenerator()
        gen.add_entry(make_entry(url="https://a.com", title="A", tags=["t1"], score=1.0, source="blog"))
        gen.add_entries([
            make_entry(url="https://b.com", title="B", tags=["t2"], score=2.0, source="blog"),
            make_entry(url="https://c.com", title="C", tags=["t3"], score=3.0, source="docs"),
        ])
        digest = gen.generate(group_by="source")
        # The digest holds exactly the 3 entries that were added - nothing more.
        all_entries = [e for s in digest.sections for e in s.entries]
        assert {e.url for e in all_entries} == {"https://a.com", "https://b.com", "https://c.com"}
        # Source grouping yields one section per distinct source.
        assert {s.topic for s in digest.sections} == {"blog", "docs"}


class TestGenerateDocstringDefaults:
    def test_generate_default_args_pin_returned_fields(self):
        """Pin the corrected generate() docstring: with default args the
        returned ContentDigest carries title="Content Digest", a period_start
        ~7 days before period_end (both ISO-8601 UTC), total_entries equal to
        the number of accumulated entries, and a non-empty summary."""
        from datetime import datetime, timezone

        gen = DigestGenerator()
        gen.add_entry(make_entry(title="A", tags=["t1"], score=1.0))
        gen.add_entry(make_entry(title="B", tags=["t2"], score=2.0))
        before = datetime.now(timezone.utc)
        digest = gen.generate()
        after = datetime.now(timezone.utc)

        # title default
        assert digest.title == "Content Digest"
        # total_entries reflects the accumulated entries (not the capped sections)
        assert digest.total_entries == 2
        # summary is generated (non-empty) for a non-empty digest
        assert digest.summary
        # period_end is ~now; period_start is ~7 days before period_end
        end = datetime.fromisoformat(digest.period_end)
        start = datetime.fromisoformat(digest.period_start)
        assert abs((end - after).total_seconds()) < 5
        assert abs((end - before).total_seconds()) < 5
        delta_days = (end - start).total_seconds() / 86400.0
        assert 6.9 <= delta_days <= 7.1

    def test_generate_explicit_period_args_pin_returned_fields(self):
        """Pin the corrected generate() docstring: explicit period_start /
        period_end / title are carried verbatim onto the returned digest."""
        gen = DigestGenerator()
        gen.add_entry(make_entry(title="A", tags=["t1"], score=1.0))
        digest = gen.generate(
            title="Weekly",
            period_start="2026-01-01T00:00:00+00:00",
            period_end="2026-01-07T00:00:00+00:00",
        )
        assert digest.title == "Weekly"
        assert digest.period_start == "2026-01-01T00:00:00+00:00"
        assert digest.period_end == "2026-01-07T00:00:00+00:00"
        assert digest.total_entries == 1
