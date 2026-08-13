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
    except ValueError:
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

    def _score_content(self, source_text: str, target: dict[str, Any]) -> tuple[float, bool]:
        target_text = f"{target.get('title', '')} {target.get('content', '')}"
        score = self._similarity.similarity(source_text, target_text)
        return (score * 0.5, True) if score > 0 else (0.0, False)

    def _score_temporal(self, source_time: str, target: dict[str, Any]) -> tuple[float, bool]:
        if not source_time or not target.get("saved_at"):
            return 0.0, False
        try:
            t1 = datetime.fromisoformat(source_time)
            t2 = datetime.fromisoformat(target["saved_at"])
            hours = abs((t1 - t2).total_seconds()) / 3600
            if hours < 24:
                return max(0, 0.2 * (1 - hours / 24)), True
        except (ValueError, TypeError):
            pass
        return 0.0, False

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
        src_text = f"{source.get('title', '')} {source.get('content', '')}"
        src_domain = source.get("domain", "")
        src_time = source.get("saved_at", "")

        for tid, target in self._items.items():
            if tid == item_id:
                continue

            score = 0.0
            reasons: list[str] = []

            cs, has_content = self._score_content(src_text, target)
            score += cs
            if has_content:
                reasons.append("content")

            if src_domain and target.get("domain") == src_domain:
                score += 0.3
                reasons.append("domain")

            ts, has_temporal = self._score_temporal(src_time, target)
            score += ts
            if has_temporal:
                reasons.append("temporal")

            if score >= threshold:
                results.append({
                    "id": tid,
                    "score": round(score, 3),
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
