"""Content digest module for personal-index.

Generates daily/weekly digests of new and updated content,
grouped by topics and interests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any


@dataclass
class DigestEntry:
    """A single entry in a content digest."""
    url: str
    title: str
    summary: str
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    timestamp: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "summary": self.summary,
            "tags": self.tags,
            "score": self.score,
            "timestamp": self.timestamp,
            "source": self.source,
        }


@dataclass
class DigestSection:
    """A section of the digest grouped by topic/tag."""
    topic: str
    entries: list[DigestEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)


@dataclass
class ContentDigest:
    """A complete content digest."""
    title: str
    generated_at: str
    period_start: str
    period_end: str
    sections: list[DigestSection] = field(default_factory=list)
    total_entries: int = 0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "sections": [
                {"topic": s.topic, "entries": [e.to_dict() for e in s.entries]}
                for s in self.sections
            ],
            "total_entries": self.total_entries,
            "summary": self.summary,
        }

    def format_markdown(self) -> str:
        """Format the digest as markdown."""
        lines = [
            f"# {self.title}",
            f"",
            f"**Generated:** {self.generated_at}",
            f"**Period:** {self.period_start} to {self.period_end}",
            f"**Total entries:** {self.total_entries}",
            "",
        ]

        if self.summary:
            lines.append(f"> {self.summary}")
            lines.append("")

        for section in self.sections:
            lines.append(f"## {section.topic}")
            lines.append("")
            for entry in section.entries:
                lines.append(f"### [{entry.title}]({entry.url})")
                if entry.summary:
                    lines.append(f"{entry.summary}")
                if entry.tags:
                    lines.append(f"Tags: {', '.join(entry.tags)}")
                lines.append("")

        return "\n".join(lines)

    def format_text(self) -> str:
        """Format the digest as plain text."""
        lines = [
            f"{self.title}",
            "=" * len(self.title),
            f"Generated: {self.generated_at}",
            f"Period: {self.period_start} to {self.period_end}",
            f"Total entries: {self.total_entries}",
            "",
        ]

        if self.summary:
            lines.append(self.summary)
            lines.append("")

        for section in self.sections:
            lines.append(f"[{section.topic}]")
            lines.append("-" * len(section.topic))
            for entry in section.entries:
                lines.append(f"  • {entry.title}")
                lines.append(f"    {entry.url}")
                if entry.summary:
                    lines.append(f"    {entry.summary[:100]}")
                lines.append("")

        return "\n".join(lines)


class DigestGenerator:
    """Generates content digests from indexed content.

    Groups content by topics/tags and generates formatted
    digest reports.
    """

    def __init__(self):
        self._entries: list[DigestEntry] = []

    def add_entry(self, entry: DigestEntry) -> None:
        """Add an entry to the digest."""
        self._entries.append(entry)

    def add_entries(self, entries: list[DigestEntry]) -> None:
        """Add multiple entries."""
        self._entries.extend(entries)

    def generate(
        self,
        title: str = "Content Digest",
        period_start: str | None = None,
        period_end: str | None = None,
        group_by: str = "tags",
        max_entries_per_section: int = 10,
    ) -> ContentDigest:
        """Generate a content digest.

        Args:
            title: Digest title.
            period_start: Start of the digest period.
            period_end: End of the digest period.
            group_by: How to group entries ('tags', 'source', 'none').
            max_entries_per_section: Max entries per section.

        Returns:
            ContentDigest with grouped entries.
        """
        now = datetime.now(timezone.utc).isoformat()

        if period_start is None:
            period_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        if period_end is None:
            period_end = now

        entries = sorted(self._entries, key=lambda e: e.score, reverse=True)

        if group_by == "none":
            sections = [DigestSection(
                topic="All Content",
                entries=entries[:max_entries_per_section],
            )]
        elif group_by == "source":
            sections = self._group_by_source(entries, max_entries_per_section)
        else:  # tags
            sections = self._group_by_tags(entries, max_entries_per_section)

        # Generate summary
        summary = self._generate_summary(sections)

        return ContentDigest(
            title=title,
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            sections=sections,
            total_entries=len(entries),
            summary=summary,
        )

    def _group_by_tags(
        self,
        entries: list[DigestEntry],
        max_per_section: int,
    ) -> list[DigestSection]:
        """Group entries by their tags."""
        tag_entries: dict[str, list[DigestEntry]] = {}
        untagged: list[DigestEntry] = []

        for entry in entries:
            if entry.tags:
                for tag in entry.tags:
                    tag_entries.setdefault(tag, []).append(entry)
            else:
                untagged.append(entry)

        sections = []
        for tag in sorted(tag_entries.keys()):
            section_entries = tag_entries[tag][:max_per_section]
            if section_entries:
                sections.append(DigestSection(topic=tag, entries=section_entries))

        if untagged:
            sections.append(DigestSection(
                topic="Uncategorized",
                entries=untagged[:max_per_section],
            ))

        return sections

    def _group_by_source(
        self,
        entries: list[DigestEntry],
        max_per_section: int,
    ) -> list[DigestSection]:
        """Group entries by their source."""
        source_entries: dict[str, list[DigestEntry]] = {}

        for entry in entries:
            source = entry.source or "Unknown"
            source_entries.setdefault(source, []).append(entry)

        sections = []
        for source in sorted(source_entries.keys()):
            section_entries = source_entries[source][:max_per_section]
            if section_entries:
                sections.append(DigestSection(topic=source, entries=section_entries))

        return sections

    def _generate_summary(self, sections: list[DigestSection]) -> str:
        """Generate a summary of the digest."""
        total = sum(s.count for s in sections)
        if total == 0:
            return "No new content found."

        section_names = [s.topic for s in sections[:5]]
        if len(sections) > 5:
            section_names.append(f"...and {len(sections) - 5} more")

        return (
            f"{total} new items across {len(sections)} topics: "
            + ", ".join(section_names)
        )

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
