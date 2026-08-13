"""Link preview module that generates Open Graph cards from URLs.

Extracts Open Graph (og:*) and Twitter Card meta tags from HTML,
falling back to standard meta tags when structured tags are missing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class LinkPreview:
    """Structured preview card for a URL, populated from OG/Twitter meta tags.

    Fields follow the Open Graph protocol with Twitter Card fallbacks.
    Priority chain: og:* > twitter:* > standard meta > HTML title tag.
    """

    title: str = ""
    description: str = ""
    image_url: str = ""
    site_name: str = ""
    type: str = ""
    url: str = ""
    twitter_card: str = ""
    locale: str = ""


class LinkPreviewGenerator:
    """Generates LinkPreview cards from HTML content.

    Extracts Open Graph and Twitter Card meta tags, with graceful fallback
    to standard HTML meta tags and the <title> element.

    Example:
        >>> generator = LinkPreviewGenerator()
        >>> preview = generator.generate(html_content, "http://example.com")
        >>> print(preview.title)
    """

    def generate(self, html: str, base_url: str = "") -> LinkPreview:
        """Generate a LinkPreview from HTML content."""
        if not html:
            return LinkPreview()

        soup = BeautifulSoup(html, "html.parser")
        preview = LinkPreview()
        preview.title = (
            self._extract_og_tag(soup, "og:title")
            or self._extract_twitter_tag(soup, "twitter:title")
            or self._extract_title_tag(soup)
        )
        preview.description = self._fallback_chain(soup, "description", "og:description", "twitter:description")
        preview.image_url = self._resolve_image_url(
            self._og_or_twitter(soup, "image"), base_url
        )
        for field in ("site_name", "type", "url", "locale"):
            setattr(preview, field, self._extract_og_tag(soup, f"og:{field}"))
        preview.twitter_card = self._extract_twitter_tag(soup, "twitter:card")
        return preview

    def _fallback_chain(
        self, soup: BeautifulSoup, meta_name: str, og_name: str, tw_name: str
    ) -> str:
        """Extract value via og > twitter > standard meta fallback chain."""
        return (
            self._extract_og_tag(soup, og_name)
            or self._extract_twitter_tag(soup, tw_name)
            or self._extract_meta(soup, meta_name)
        )

    def _og_or_twitter(self, soup: BeautifulSoup, name: str) -> str:
        """Extract value from og or twitter tag."""
        return self._extract_og_tag(soup, f"og:{name}") or self._extract_twitter_tag(soup, f"twitter:{name}")

    def _extract_og_tag(self, soup: BeautifulSoup, property_name: str) -> str:
        """Extract an Open Graph meta tag value."""
        tag = soup.find("meta", attrs={"property": property_name})
        if tag and tag.get("content"):
            content = tag["content"]
            if isinstance(content, str):
                return content.strip()
            return str(content).strip()
        return ""

    def _extract_twitter_tag(self, soup: BeautifulSoup, name: str) -> str:
        """Extract a Twitter Card meta tag value."""
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            content = tag["content"]
            if isinstance(content, str):
                return content.strip()
            return str(content).strip()
        return ""

    def _extract_meta(self, soup: BeautifulSoup, name: str) -> str:
        """Extract a standard meta tag value."""
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            content = tag["content"]
            if isinstance(content, str):
                return content.strip()
            return str(content).strip()
        return ""

    def _extract_title_tag(self, soup: BeautifulSoup) -> str:
        """Extract the <title> element text."""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        return ""

    def _resolve_image_url(self, image_url: str, base_url: str) -> str:
        """Resolve a potentially relative image URL against the base URL."""
        if not image_url:
            return ""
        if not base_url:
            return image_url
        return urljoin(base_url, image_url)
