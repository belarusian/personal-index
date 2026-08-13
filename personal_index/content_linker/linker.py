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

    def _score_content(self, src: str, t: dict[str, Any]) -> tuple[float, bool]:
        s = self._similarity.similarity(src, f"{t.get('title', '')} {t.get('content', '')}")
        return (s * 0.5, True) if s > 0 else (0.0, False)

    def _score_temporal(self, st: str, t: dict[str, Any]) -> tuple[float, bool]:
        if not st or not t.get("saved_at"):
            return 0.0, False
        try:
            h = abs((datetime.fromisoformat(st) - datetime.fromisoformat(t["saved_at"])).total_seconds()) / 3600
            if h < 24:
                return max(0, 0.2 * (1 - h / 24)), True
        except (ValueError, TypeError):
            pass
        return 0.0, False

    def _score_target(
        self, src_text: str, src_domain: str, src_time: str,
        target: dict[str, Any],
    ) -> tuple[float, list[str]]:
        score, reasons = 0.0, []
        cs, hc = self._score_content(src_text, target)
        score += cs
        if hc:
            reasons.append("content")
        if src_domain and target.get("domain") == src_domain:
            score += 0.3
            reasons.append("domain")
        ts, ht = self._score_temporal(src_time, target)
        score += ts
        if ht:
            reasons.append("temporal")
        return score, reasons

    def find_related(
        self, item_id: str, threshold: float = 0.1, limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find items related to the given item."""
        if item_id in self._link_cache:
            return self._link_cache[item_id]
        source = self._items.get(item_id)
        if not source:
            return []

        src_text = f"{source.get('title', '')} {source.get('content', '')}"
        src_domain = source.get("domain", "")
        src_time = source.get("saved_at", "")
        results: list[dict[str, Any]] = []

        for tid, target in self._items.items():
            if tid == item_id:
                continue
            score, reasons = self._score_target(src_text, src_domain, src_time, target)
            if score >= threshold:
                results.append({
                    "id": tid, "score": round(score, 3),
                    "title": target.get("title", ""), "reasons": reasons,
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        self._link_cache[item_id] = results[:limit]
        return results[:limit]

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
