"""Content digest module for generating content summaries and digests.

Creates daily/weekly/monthly digest emails and reports from
indexed content, highlighting new and important items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class DigestFrequency(Enum):
    """How often digests should be generated."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class DigestConfig:
    """Configuration for digest generation.

    Attributes:
        frequency: How often to generate digests.
        max_items: Maximum items per digest.
        min_score: Minimum content score to include.
        include_tags: Whether to include tag information.
        include_preview: Whether to include content previews.
        preview_length: Character limit for previews.
        group_by: How to group items (tag, domain, date).
        sort_by: How to sort items (score, date, title).
    """

    frequency: DigestFrequency = DigestFrequency.DAILY
    max_items: int = 20
    min_score: float = 0.0
    include_tags: bool = True
    include_preview: bool = True
    preview_length: int = 200
    group_by: str = "date"
    sort_by: str = "score"


@dataclass
class DigestItem:
    """A single item in a digest.

    Attributes:
        title: Content title.
        url: Content URL.
        preview: Content preview text.
        tags: Content tags.
        score: Content score.
        published_at: Publication date.
        domain: Source domain.
    """

    title: str
    url: str
    preview: str = ""
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    published_at: datetime | None = None
    domain: str = ""


@dataclass
class ContentDigest:
    """A complete content digest.

    Attributes:
        title: Digest title.
        period_start: Start of the digest period.
        period_end: End of the digest period.
        items: Items included in the digest.
        total_new: Total new items in period.
        top_tags: Most common tags.
        top_domains: Most common source domains.
    """

    title: str
    period_start: datetime
    period_end: datetime
    items: list[DigestItem] = field(default_factory=list)
    total_new: int = 0
    top_tags: list[str] = field(default_factory=list)
    top_domains: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert digest to dictionary."""
        return {
            "title": self.title,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "items": [
                {
                    "title": i.title,
                    "url": i.url,
                    "preview": i.preview,
                    "tags": i.tags,
                    "score": i.score,
                }
                for i in self.items
            ],
            "total_new": self.total_new,
            "top_tags": self.top_tags,
            "top_domains": self.top_domains,
        }


class DigestGenerator:
    """Generates content digests from indexed items.

    Filters, sorts, and formats content items into digest
    reports based on configurable criteria.
    """

    def __init__(self, config: DigestConfig | None = None) -> None:
        self.config = config or DigestConfig()

    def generate(
        self,
        items: list[dict[str, Any]],
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> ContentDigest:
        """Generate a digest from content items.

        Args:
            items: List of content items.
            period_start: Start of digest period.
            period_end: End of digest period.

        Returns:
            ContentDigest with filtered and formatted items.
        """
        if period_end is None:
            period_end = datetime.now()
        if period_start is None:
            delta = self._get_period_delta()
            period_start = period_end - delta

        # Filter items by period and score
        filtered = self._filter_items(items, period_start, period_end)

        # Sort items
        sorted_items = self._sort_items(filtered)

        # Limit items
        sorted_items = sorted_items[: self.config.max_items]

        # Convert to digest items
        digest_items = [self._to_digest_item(item) for item in sorted_items]

        # Compute statistics
        top_tags = self._compute_top_tags(filtered, 5)
        top_domains = self._compute_top_domains(filtered, 5)

        title = self._generate_title(period_start, period_end)

        return ContentDigest(
            title=title,
            period_start=period_start,
            period_end=period_end,
            items=digest_items,
            total_new=len(filtered),
            top_tags=top_tags,
            top_domains=top_domains,
        )

    def _get_period_delta(self) -> timedelta:
        """Get the time delta for the digest period."""
        deltas = {
            DigestFrequency.DAILY: timedelta(days=1),
            DigestFrequency.WEEKLY: timedelta(weeks=1),
            DigestFrequency.MONTHLY: timedelta(days=30),
        }
        return deltas.get(self.config.frequency, timedelta(days=1))

    def _filter_items(
        self,
        items: list[dict[str, Any]],
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Filter items by date range and minimum score."""
        filtered = []
        for item in items:
            score = item.get("score", 0.0)
            if score < self.config.min_score:
                continue

            pub_date = item.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    pub_date = datetime.fromisoformat(pub_date)
                if not (start <= pub_date <= end):
                    continue

            filtered.append(item)
        return filtered

    def _sort_items(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sort items by configured sort field."""
        sort_keys = {
            "score": lambda x: x.get("score", 0.0),
            "date": lambda x: x.get("published_at") or datetime.min,
            "title": lambda x: x.get("title", ""),
        }
        key_func = sort_keys.get(self.config.sort_by, sort_keys["score"])
        reverse = self.config.sort_by != "title"
        return sorted(items, key=key_func, reverse=reverse)

    def _to_digest_item(self, item: dict[str, Any]) -> DigestItem:
        """Convert a content item to a digest item."""
        preview = ""
        if self.config.include_preview:
            desc = item.get("description", item.get("content", ""))
            if isinstance(desc, str):
                preview = desc[: self.config.preview_length]

        tags = item.get("tags", [])
        if not self.config.include_tags:
            tags = []

        url = item.get("url", "")
        domain = ""
        if "://" in url:
            domain = url.split("://")[1].split("/")[0]

        return DigestItem(
            title=item.get("title", "Untitled"),
            url=url,
            preview=preview,
            tags=tags if isinstance(tags, list) else [],
            score=item.get("score", 0.0),
            published_at=item.get("published_at"),
            domain=domain,
        )

    def _compute_top_tags(
        self,
        items: list[dict[str, Any]],
        limit: int = 5,
    ) -> list[str]:
        """Compute the most common tags."""
        tag_count: dict[str, int] = {}
        for item in items:
            for tag in item.get("tags", []):
                tag_count[tag] = tag_count.get(tag, 0) + 1
        sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags[:limit]]

    def _compute_top_domains(
        self,
        items: list[dict[str, Any]],
        limit: int = 5,
    ) -> list[str]:
        """Compute the most common source domains."""
        domain_count: dict[str, int] = {}
        for item in items:
            url = item.get("url", "")
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                domain_count[domain] = domain_count.get(domain, 0) + 1
        sorted_domains = sorted(
            domain_count.items(), key=lambda x: x[1], reverse=True,
        )
        return [domain for domain, _ in sorted_domains[:limit]]

    def _generate_title(
        self,
        start: datetime,
        end: datetime,
    ) -> str:
        """Generate a title for the digest."""
        freq_label = {
            DigestFrequency.DAILY: "Daily",
            DigestFrequency.WEEKLY: "Weekly",
            DigestFrequency.MONTHLY: "Monthly",
        }
        label = freq_label.get(self.config.frequency, "Content")
        return f"{label} Digest: {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
