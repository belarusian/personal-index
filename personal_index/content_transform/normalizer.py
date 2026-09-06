"""Content normalization utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ContentNormalizer:
    """Normalizes content fields to consistent formats.

    Attributes:
        normalize_titles: Whether to normalize title casing.
        normalize_urls: Whether to normalize URLs.
        normalize_tags: Whether to normalize tag format.
    """

    normalize_titles: bool = True
    normalize_urls: bool = True
    normalize_tags: bool = True

    def normalize(self, content: dict[str, Any]) -> dict[str, Any]:
        """Normalize a content item.

        Args:
            content: Content item to normalize.

        Returns:
            Normalized content item.
        """
        result = dict(content)

        if self.normalize_titles and "title" in result:
            result["title"] = self._normalize_title(str(result["title"]))

        if self.normalize_urls and "url" in result:
            result["url"] = self._normalize_url(str(result["url"]))

        if self.normalize_tags and "tags" in result:
            tags = result["tags"]
            if isinstance(tags, list):
                result["tags"] = [
                    self._normalize_tag(str(t)) for t in tags
                ]

        return result

    def normalize_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalize multiple content items.

        Args:
            items: List of content items.

        Returns:
            List of normalized content items.
        """
        return [self.normalize(item) for item in items]

    def _normalize_title(self, title: str) -> str:
        """Normalize title to title case."""
        return title.strip().title()

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL value.

        Behavior (in order):
        1. Strip surrounding whitespace.
        2. If the stripped value is non-empty and does not already start
           with "http", prepend "https://".
        3. Remove trailing "/" characters from the result when it is
           longer than one character (a one-character value is returned
           unchanged).

        Note: because the "https://" prefix is applied before the
        trailing-slash strip, a lone "/" becomes "https:" (the prefix
        "https://" plus the slash, then the trailing slashes are
        removed). There is no lone-slash exception.
        """
        url = url.strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        # Remove trailing slash
        if len(url) > 1:
            url = url.rstrip("/")
        return url

    def _normalize_tag(self, tag: str) -> str:
        """Normalize a tag into a canonical slug form.

        1. Strips surrounding whitespace and lowercases the value.
        2. Replaces every character not in [a-z0-9-] with a single "-".
        3. Collapses runs of consecutive "-" into a single "-".
        4. Strips leading and trailing "-".
        """
        tag = tag.strip().lower()
        tag = re.sub(r"[^a-z0-9-]", "-", tag)
        tag = re.sub(r"-+", "-", tag)
        return tag.strip("-")
