"""Content report generation for personal-index.

Generates structured reports about saved content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ReportFormat(str, Enum):
    """Supported report output formats."""

    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


@dataclass
class ReportSection:
    """A section within a report."""

    title: str
    content: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "data": self.data,
        }


@dataclass
class ReportFilter:
    """Filter criteria for report generation."""

    min_word_count: Optional[int] = None
    max_word_count: Optional[int] = None
    categories: list[str] = field(default_factory=list)
    min_engagement: Optional[float] = None
    max_engagement: Optional[float] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    def matches_word_count(self, word_count: int) -> bool:
        """Check if word count matches filter."""
        if self.min_word_count is not None and word_count < self.min_word_count:
            return False
        if self.max_word_count is not None and word_count > self.max_word_count:
            return False
        return True

    def matches_category(self, category: str) -> bool:
        """Check if category matches filter."""
        if not self.categories:
            return True
        return category in self.categories

    def matches_engagement(self, engagement: float) -> bool:
        """Check if engagement score matches filter."""
        if self.min_engagement is not None and engagement < self.min_engagement:
            return False
        if self.max_engagement is not None and engagement > self.max_engagement:
            return False
        return True

    def matches_all(
        self, word_count: int, category: str, engagement: float
    ) -> bool:
        """Check if all filter criteria match."""
        return (
            self.matches_word_count(word_count)
            and self.matches_category(category)
            and self.matches_engagement(engagement)
        )


@dataclass
class ContentReport:
    """A generated content report."""

    title: str
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    format: str = ReportFormat.TEXT.value
    sections: list[ReportSection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_section(self, section: ReportSection) -> None:
        """Add a section to the report."""
        self.sections.append(section)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "format": self.format,
            "sections": [s.to_dict() for s in self.sections],
            "metadata": self.metadata,
        }

    def to_text(self) -> str:
        """Render report as plain text."""
        lines = [f"# {self.title}", f"Generated: {self.generated_at}", ""]
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append(section.content)
            if section.data:
                for key, value in section.data.items():
                    lines.append(f"  {key}: {value}")
            lines.append("")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Render report as markdown."""
        lines = [f"# {self.title}", f"*Generated: {self.generated_at}*", ""]
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append(section.content)
            if section.data:
                lines.append("| Key | Value |")
                lines.append("|-----|-------|")
                for key, value in section.data.items():
                    lines.append(f"| {key} | {value} |")
            lines.append("")
        return "\n".join(lines)

    def to_html(self) -> str:
        """Render report as HTML."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head><title>",
            self.title,
            "</title></head><body>",
            f"<h1>{self.title}</h1>",
            f"<p>Generated: {self.generated_at}</p>",
        ]
        for section in self.sections:
            html_parts.append(f"<h2>{section.title}</h2>")
            html_parts.append(f"<p>{section.content}</p>")
            if section.data:
                html_parts.append("<table>")
                for key, value in section.data.items():
                    html_parts.append(
                        f"<tr><td>{key}</td><td>{value}</td></tr>"
                    )
                html_parts.append("</table>")
        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def render(self) -> str:
        """Render report in the configured format."""
        if self.format == ReportFormat.MARKDOWN.value:
            return self.to_markdown()
        elif self.format == ReportFormat.HTML.value:
            return self.to_html()
        elif self.format == ReportFormat.JSON.value:
            import json
            return json.dumps(self.to_dict(), indent=2)
        else:
            return self.to_text()


class ContentReportGenerator:
    """Generates content reports from content items."""

    def __init__(self) -> None:
        self._items: list[dict] = []

    def add_items(self, items: list[dict]) -> None:
        """Add content items for reporting."""
        self._items.extend(items)

    def generate_summary_report(
        self,
        title: str = "Content Summary Report",
        fmt: ReportFormat = ReportFormat.TEXT,
        filter: Optional[ReportFilter] = None,
    ) -> ContentReport:
        """Generate a summary report."""
        filtered = self._items
        if filter:
            filtered = [
                item for item in self._items
                if filter.matches_all(
                    item.get("word_count", 0),
                    item.get("category", "Uncategorized"),
                    item.get("engagement_score", 0.0),
                )
            ]

        report = ContentReport(title=title, format=fmt.value)

        # Overview section
        report.add_section(ReportSection(
            title="Overview",
            content=f"Total items: {len(filtered)}",
            data={
                "total_items": len(filtered),
                "filtered_from": len(self._items),
            },
        ))

        # Word count stats
        word_counts = [item.get("word_count", 0) for item in filtered]
        if word_counts:
            report.add_section(ReportSection(
                title="Word Count Statistics",
                content="Word count analysis for filtered items.",
                data={
                    "total_words": sum(word_counts),
                    "avg_words": round(sum(word_counts) / len(word_counts), 2),
                    "max_words": max(word_counts),
                    "min_words": min(word_counts),
                },
            ))

        # Category breakdown
        categories: dict[str, int] = {}
        for item in filtered:
            cat = item.get("category", "Uncategorized")
            categories[cat] = categories.get(cat, 0) + 1
        if categories:
            report.add_section(ReportSection(
                title="Category Breakdown",
                content="Content distribution by category.",
                data={k: v for k, v in sorted(categories.items(), key=lambda x: -x[1])},
            ))

        # Top items
        sorted_items = sorted(
            filtered,
            key=lambda x: x.get("engagement_score", 0),
            reverse=True,
        )
        top_items = sorted_items[:10]
        if top_items:
            top_data = {
                f"#{i+1} {item.get('title', item.get('url', 'Unknown'))}":
                item.get("engagement_score", 0)
                for i, item in enumerate(top_items)
            }
            report.add_section(ReportSection(
                title="Top Engaged Content",
                content="Top 10 most engaged content items.",
                data=top_data,
            ))

        return report
