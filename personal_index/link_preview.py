"""Link preview module that generates Open Graph cards from URLs.

Extracts Open Graph (og:*) and Twitter Card meta tags from HTML,
falling back to standard meta tags when structured tags are missing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
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
        """Generate a LinkPreview from HTML content.

        Args:
            html: Raw HTML string to parse.
            base_url: Base URL for resolving relative image URLs.

        Returns:
            A LinkPreview with extracted metadata.
        """
        if not html:
            return LinkPreview()

        soup = BeautifulSoup(html, "html.parser")
        preview = LinkPreview()

        # Priority: og:title > twitter:title > <title> tag
        preview.title = (
            self._extract_og_tag(soup, "og:title")
            or self._extract_twitter_tag(soup, "twitter:title")
            or self._extract_title_tag(soup)
        )

        # Priority: og:description > twitter:description > meta description
        preview.description = (
            self._extract_og_tag(soup, "og:description")
            or self._extract_twitter_tag(soup, "twitter:description")
            or self._extract_meta(soup, "description")
        )

        # Priority: og:image > twitter:image
        preview.image_url = self._resolve_image_url(
            self._extract_og_tag(soup, "og:image")
            or self._extract_twitter_tag(soup, "twitter:image"),
            base_url,
        )

        # Other OG fields
        preview.site_name = self._extract_og_tag(soup, "og:site_name")
        preview.type = self._extract_og_tag(soup, "og:type")
        preview.url = self._extract_og_tag(soup, "og:url")
        preview.locale = self._extract_og_tag(soup, "og:locale")

        # Twitter card type (always extracted, even if OG is present)
        preview.twitter_card = self._extract_twitter_tag(soup, "twitter:card")

        return preview

    def _extract_og_tag(self, soup: BeautifulSoup, property_name: str) -> str:
        """Extract an Open Graph meta tag value."""
        tag = soup.find("meta", attrs={"property": property_name})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""

    def _extract_twitter_tag(self, soup: BeautifulSoup, name: str) -> str:
        """Extract a Twitter Card meta tag value."""
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""

    def _extract_meta(self, soup: BeautifulSoup, name: str) -> str:
        """Extract a standard meta tag value."""
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()
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
