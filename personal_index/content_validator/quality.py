"""Content quality checker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityScore:
    """Quality assessment for a content item.

    Attributes:
        overall: Overall quality score (0.0 to 1.0).
        completeness: How complete the item is.
        richness: How rich the content is.
        issues: List of quality issues found.
    """

    overall: float = 0.0
    completeness: float = 0.0
    richness: float = 0.0
    issues: list[str] = field(default_factory=list)


@dataclass
class QualityChecker:
    """Checks content quality and assigns scores.

    Attributes:
        required_fields: Fields that contribute to completeness.
        rich_fields: Fields that contribute to richness.
    """

    required_fields: list[str] = field(
        default_factory=lambda: ["id", "title", "content"]
    )
    rich_fields: list[str] = field(
        default_factory=lambda: ["tags", "author", "summary", "score"]
    )

    def check(self, item: dict[str, Any]) -> QualityScore:
        """Check the quality of a content item.

        Args:
            item: Content item to check.

        Returns:
            QualityScore with assessment details.
        """
        issues: list[str] = []

        # Check completeness
        present = sum(1 for f in self.required_fields if item.get(f))
        completeness = present / len(self.required_fields) if self.required_fields else 0.0

        # Check richness
        rich_present = sum(1 for f in self.rich_fields if item.get(f))
        richness = rich_present / len(self.rich_fields) if self.rich_fields else 0.0

        # Identify issues
        for f in self.required_fields:
            if not item.get(f):
                issues.append(f"Missing required field: {f}")

        if item.get("title") and len(str(item["title"])) < 3:
            issues.append("Title is too short")

        if item.get("content") and len(str(item["content"])) < 10:
            issues.append("Content is too short")

        overall = round((completeness * 0.6 + richness * 0.4), 4)

        return QualityScore(
            overall=overall,
            completeness=round(completeness, 4),
            richness=round(richness, 4),
            issues=issues,
        )

    def check_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], QualityScore]]:
        """Check quality of multiple items.

        Args:
            items: List of content items.

        Returns:
            List of (item, QualityScore) tuples.
        """
        return [(item, self.check(item)) for item in items]

    def filter_by_quality(
        self,
        items: list[dict[str, Any]],
        min_score: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Filter items by minimum quality score.

        Args:
            items: List of content items.
            min_score: Minimum quality score threshold.

        Returns:
            List of items meeting quality threshold.
        """
        return [
            item for item in items
            if self.check(item).overall >= min_score
        ]
