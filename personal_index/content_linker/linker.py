"""High-level content linker - finds related saved items."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from personal_index.content_linker.link import Link, LinkType
from personal_index.content_linker.similarity import SimilarityEngine


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.hostname or ""
    except Exception:
        return ""


class ContentLinker:
    """Finds and manages relationships between saved content items."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._similarity = SimilarityEngine()
        self._link_cache: dict[str, list[dict[str, Any]]] = {}

    def add_item(
        self,
        item_id: str,
        content: str,
        url: str = "",
        saved_at: str | None = None,
        title: str = "",
    ) -> None:
        """Add a content item to the linker."""
        self._items[item_id] = {
            "id": item_id,
            "content": content,
            "url": url,
            "saved_at": saved_at or datetime.now(timezone.utc).isoformat(),
            "title": title,
            "domain": _extract_domain(url),
        }
        self._link_cache.pop(item_id, None)

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        """Get a content item by ID."""
        return self._items.get(item_id)

    def get_all_items(self) -> list[dict[str, Any]]:
        """Get all stored items."""
        return list(self._items.values())

    def remove_item(self, item_id: str) -> None:
        """Remove a content item."""
        self._items.pop(item_id, None)
        self._link_cache.pop(item_id, None)

    def find_related(
        self,
        item_id: str,
        threshold: float = 0.1,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find items related to the given item."""
        if item_id in self._link_cache:
            return self._link_cache[item_id]

        source = self._items.get(item_id)
        if not source:
            return []

        results: list[dict[str, Any]] = []
        source_text = f"{source.get('title', '')} {source.get('content', '')}"
        source_domain = source.get("domain", "")
        source_time = source.get("saved_at", "")

        for target_id, target in self._items.items():
            if target_id == item_id:
                continue

            combined_score = 0.0
            reasons: list[str] = []

            # Content similarity
            target_text = f"{target.get('title', '')} {target.get('content', '')}"
            content_score = self._similarity.similarity(source_text, target_text)
            if content_score > 0:
                combined_score += content_score * 0.5
                reasons.append("content")

            # Domain match
            if source_domain and target.get("domain") == source_domain:
                combined_score += 0.3
                reasons.append("domain")

            # Temporal proximity
            if source_time and target.get("saved_at"):
                try:
                    t1 = datetime.fromisoformat(source_time)
                    t2 = datetime.fromisoformat(target["saved_at"])
                    hours_diff = abs((t1 - t2).total_seconds()) / 3600
                    if hours_diff < 24:
                        temporal_score = max(0, 0.2 * (1 - hours_diff / 24))
                        combined_score += temporal_score
                        reasons.append("temporal")
                except (ValueError, TypeError):
                    pass

            if combined_score >= threshold:
                results.append({
                    "id": target_id,
                    "score": round(combined_score, 3),
                    "title": target.get("title", ""),
                    "reasons": reasons,
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        results = results[:limit]
        self._link_cache[item_id] = results
        return results

    def get_all_links(
        self,
        item_id: str,
        threshold: float = 0.1,
    ) -> list[Link]:
        """Get all links for an item as Link objects."""
        related = self.find_related(item_id, threshold=threshold)
        return [
            Link(
                source_id=item_id,
                target_id=r["id"],
                link_type=LinkType.CONTENT,
                score=r["score"],
            )
            for r in related
        ]

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._items.clear()
        self._link_cache.clear()
