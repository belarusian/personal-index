"""JSON export functionality for personal-index content.

Exports content items, bookmarks, tags, and metadata to JSON format
with configurable options for pretty printing and field selection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class JsonExportOptions:
    """Options for JSON export.

    Attributes:
        indent: Number of spaces for indentation (None for compact).
        sort_keys: Whether to sort dictionary keys.
        include_metadata: Whether to include content metadata.
        include_tags: Whether to include content tags.
        include_scores: Whether to include content scores.
        fields: Specific fields to include (None for all).
        exclude_fields: Fields to exclude from export.
    """

    indent: int | None = 2
    sort_keys: bool = True
    include_metadata: bool = True
    include_tags: bool = True
    include_scores: bool = False
    fields: list[str] | None = None
    exclude_fields: list[str] = field(default_factory=list)


class JsonExporter:
    """Exports content data to JSON format.

    Supports exporting individual items or collections with
    configurable field selection and formatting.
    """

    def __init__(self, options: JsonExportOptions | None = None) -> None:
        self.options = options or JsonExportOptions()

    def export_item(self, item: dict[str, Any]) -> str:
        """Export a single content item to JSON string.

        Args:
            item: Content item dictionary.

        Returns:
            JSON string representation of the item.
        """
        filtered = self._filter_fields(item)
        return json.dumps(filtered, indent=self.options.indent,
                         sort_keys=self.options.sort_keys,
                         default=str)

    def export_items(self, items: list[dict[str, Any]]) -> str:
        """Export multiple content items to JSON string.

        Args:
            items: List of content item dictionaries.

        Returns:
            JSON string representation of the items list.
        """
        filtered = [self._filter_fields(item) for item in items]
        return json.dumps(filtered, indent=self.options.indent,
                         sort_keys=self.options.sort_keys,
                         default=str)

    def export_to_file(
        self,
        items: list[dict[str, Any]],
        filepath: str | Path,
    ) -> int:
        """Export items to a JSON file.

        Args:
            items: List of content item dictionaries.
            filepath: Path to the output file.

        Returns:
            Number of items exported.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.export_items(items)
        filepath.write_text(content, encoding="utf-8")
        return len(items)

    def export_collection(
        self,
        name: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Export a named collection with metadata.

        Args:
            name: Name of the collection.
            items: List of content items.
            metadata: Optional collection metadata.

        Returns:
            JSON string of the collection.
        """
        collection = {
            "collection_name": name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "item_count": len(items),
            "items": [self._filter_fields(item) for item in items],
        }
        if metadata:
            collection["metadata"] = metadata
        return json.dumps(collection, indent=self.options.indent,
                         sort_keys=self.options.sort_keys,
                         default=str)

    def _filter_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        """Filter item fields based on export options.

        Sub-steps, in order:
          1. Copy the item into a new dict (the input is not mutated).
          2. Pop "metadata" when include_metadata is False.
          3. Pop "tags" when include_tags is False.
          4. Pop BOTH "score" and "score_details" when include_scores
             is False.
          5. Pop every name in exclude_fields.
          6. When fields is a non-empty whitelist, keep only the keys
             present in fields (applied last, so it can override the
             earlier pops).

        Returns the filtered dict.
        """
        result = dict(item)

        if not self.options.include_metadata:
            result.pop("metadata", None)

        if not self.options.include_tags:
            result.pop("tags", None)

        if not self.options.include_scores:
            result.pop("score", None)
            result.pop("score_details", None)

        for field_name in self.options.exclude_fields:
            result.pop(field_name, None)

        if self.options.fields:
            result = {
                k: v for k, v in result.items()
                if k in self.options.fields
            }

        return result

    def export_summary(
        self,
        items: list[dict[str, Any]],
    ) -> str:
        """Export a summary of the collection.

        Args:
            items: List of content items.

        Returns:
            JSON string with summary statistics.
        """
        total = len(items)
        tagged = sum(1 for i in items if i.get("tags"))
        bookmarked = sum(1 for i in items if i.get("bookmarked"))

        domains = set()
        for item in items:
            url = item.get("url", "")
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                domains.add(domain)

        summary = {
            "total_items": total,
            "tagged_items": tagged,
            "bookmarked_items": bookmarked,
            "unique_domains": len(domains),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(summary, indent=self.options.indent,
                         sort_keys=self.options.sort_keys)


def export_json(results, tag_store=None) -> str:
    """Export search results as JSON.

    Args:
        results: List of SearchResult objects.
        tag_store: Optional TagStore for tag information.

    Returns:
        JSON formatted string of results.
    """
    items = []
    for result in results:
        item = {
            "url": result.url,
            "title": result.title,
            "snippet": result.snippet,
            "relevance_score": result.relevance_score,
        }
        if tag_store:
            tags = tag_store.get_tags_for_page(result.url)
            item["tags"] = [t.name for t in tags]
        items.append(item)
    return json.dumps(items, indent=2, default=str)
