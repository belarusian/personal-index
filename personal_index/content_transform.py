"""Content transformation pipeline for personal-index.

Provides a chain of transformation functions that can be
applied to content items for normalization, enrichment,
and formatting.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

TransformFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class TransformPipeline:
    """A pipeline of content transformations.

    Attributes:
        name: Pipeline name.
        transforms: Ordered list of transformation functions.
        metadata: Pipeline metadata.
    """

    name: str = "default"
    transforms: list[tuple[str, TransformFn]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(
        self,
        name: str,
        transform: TransformFn,
    ) -> TransformPipeline:
        """Add a transformation to the pipeline.

        Args:
            name: Name of the transformation.
            transform: Transformation function.

        Returns:
            Self for chaining.
        """
        self.transforms.append((name, transform))
        return self

    def apply(self, item: dict[str, Any]) -> dict[str, Any]:
        """Apply all transformations to an item.

        Args:
            item: Content item to transform.

        Returns:
            Transformed content item.
        """
        result = dict(item)
        for name, transform in self.transforms:
            try:
                result = transform(result)
            except (ValueError, TypeError, KeyError):
                # Skip failed transforms, continue pipeline
                import logging
                logging.getLogger(__name__).debug("Transform failed, skipping")
        return result

    def apply_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply pipeline to a batch of items.

        Args:
            items: List of content items.

        Returns:
            List of transformed items.
        """
        return [self.apply(item) for item in items]


# Built-in transforms


def normalize_url(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize URL by removing trailing slashes and fragments."""
    url = item.get("url", "")
    if url:
        url = url.rstrip("/")
        if "#" in url:
            url = url.split("#")[0]
        item["url"] = url
    return item


def normalize_title(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize title by stripping whitespace and lowercasing."""
    title = item.get("title", "")
    if title:
        item["title"] = title.strip()
    return item


def normalize_tags(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize tags by lowercasing and stripping."""
    tags = item.get("tags", [])
    if isinstance(tags, list):
        item["tags"] = [
            tag.strip().lower() for tag in tags if tag
        ]
    return item


def add_domain(item: dict[str, Any]) -> dict[str, Any]:
    """Extract and add domain from URL."""
    url = item.get("url", "")
    if "://" in url:
        domain = url.split("://")[1].split("/")[0]
        item["domain"] = domain
    return item


def add_word_count(item: dict[str, Any]) -> dict[str, Any]:
    """Add word count from content or description."""
    content = item.get("content", item.get("description", ""))
    if isinstance(content, str):
        item["word_count"] = len(content.split())
    return item


def add_timestamp(item: dict[str, Any]) -> dict[str, Any]:
    """Add processing timestamp."""
    item["processed_at"] = datetime.now(timezone.utc).isoformat()
    return item


def filter_by_score(
    min_score: float,
) -> TransformFn:
    """Create a transform that filters items below min_score.

    Args:
        min_score: Minimum score threshold.

    Returns:
        Transform function.
    """
    def transform(item: dict[str, Any]) -> dict[str, Any]:
        score = item.get("score", 0.0)
        if score < min_score:
            item["_filtered"] = True
        return item
    return transform


def enrich_with_defaults(item: dict[str, Any]) -> dict[str, Any]:
    """Add default values for missing fields."""
    defaults = {
        "tags": [],
        "score": 0.0,
        "bookmarked": False,
        "metadata": {},
    }
    for key, value in defaults.items():
        if key not in item:
            item[key] = value
    return item


def create_standard_pipeline() -> TransformPipeline:
    """Create a standard transformation pipeline.

    Returns:
        Configured TransformPipeline.
    """
    return TransformPipeline(name="standard").add(
        "normalize_url", normalize_url,
    ).add(
        "normalize_title", normalize_title,
    ).add(
        "normalize_tags", normalize_tags,
    ).add(
        "add_domain", add_domain,
    ).add(
        "add_word_count", add_word_count,
    ).add(
        "enrich_with_defaults", enrich_with_defaults,
    ).add(
        "add_timestamp", add_timestamp,
    )
