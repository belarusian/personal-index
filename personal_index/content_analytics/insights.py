"""Insight engine for generating content insights."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Insight:
    """A single insight about content.

    Attributes:
        title: Short title of the insight.
        description: Detailed description.
        severity: Severity level (info, warning, critical).
        category: Category of insight.
        value: Numeric value associated with insight.
    """

    title: str
    description: str
    severity: str = "info"
    category: str = "general"
    value: float | None = None


@dataclass
class InsightEngine:
    """Generates insights from content data.

    Attributes:
        min_items_for_insight: Minimum items needed to generate insights.
    """

    min_items_for_insight: int = 5

    def generate_insights(
        self,
        items: list[dict[str, Any]],
    ) -> list[Insight]:
        """Generate insights from content items.

        Args:
            items: List of content item dictionaries.

        Returns:
            List of Insight objects.
        """
        if len(items) < self.min_items_for_insight:
            return []

        insights: list[Insight] = []
        insights.extend(self._analyze_tag_distribution(items))
        insights.extend(self._analyze_score_distribution(items))
        insights.extend(self._analyze_type_distribution(items))
        return insights

    def _analyze_tag_distribution(
        self,
        items: list[dict[str, Any]],
    ) -> list[Insight]:
        """Analyze tag distribution for insights."""
        tag_counts: dict[str, int] = {}
        for item in items:
            tags = item.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            return []

        most_common = max(tag_counts, key=lambda k: tag_counts[k])
        return [
            Insight(
                title="Most common tag",
                description=f"The tag '{most_common}' appears in {tag_counts[most_common]} items",
                category="tags",
                value=float(tag_counts[most_common]),
            )
        ]

    def _analyze_score_distribution(
        self,
        items: list[dict[str, Any]],
    ) -> list[Insight]:
        """Analyze score distribution for insights."""
        scores = [
            item.get("score", 0.0)
            for item in items
            if isinstance(item.get("score"), (int, float))
        ]
        if not scores:
            return []

        avg = sum(scores) / len(scores)
        _high_scores = sum(1 for s in scores if s >= 0.8)
        low_scores = sum(1 for s in scores if s < 0.3)

        insights: list[Insight] = [
            Insight(
                title="Average score",
                description=f"Average content score is {avg:.2f}",
                category="scoring",
                value=avg,
            )
        ]

        if low_scores > len(scores) * 0.5:
            insights.append(
                Insight(
                    title="Low quality content",
                    description=f"{low_scores} items have scores below 0.3",
                    severity="warning",
                    category="scoring",
                    value=float(low_scores),
                )
            )

        return insights

    def _analyze_type_distribution(
        self,
        items: list[dict[str, Any]],
    ) -> list[Insight]:
        """Analyze type distribution for insights."""
        type_counts: dict[str, int] = {}
        for item in items:
            item_type = item.get("type", "unknown")
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

        if len(type_counts) <= 1:
            return []

        dominant = max(type_counts, key=lambda k: type_counts[k])
        return [
            Insight(
                title="Dominant content type",
                description=f"'{dominant}' is the most common type with {type_counts[dominant]} items",
                category="types",
                value=float(type_counts[dominant]),
            )
        ]
