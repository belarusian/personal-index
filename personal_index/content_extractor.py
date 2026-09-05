"""Content extraction from HTML pages."""

from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ExtractedContent:
    """Content extracted from an HTML page."""

    title: str = ""
    text: str = ""
    meta_description: str = ""
    meta_keywords: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)
    images: list[tuple[str, str]] = field(default_factory=list)
    canonical_url: str = ""
    language: str = ""
    author: str = ""
    word_count: int = 0


class ContentExtractor:
    """Extracts meaningful content from HTML pages."""

    def __init__(self, max_text_length: int = 100000):
        self.max_text_length = max_text_length

    def extract(self, html: str) -> ExtractedContent:
        """Extract content from HTML string."""
        if not html:
            return ExtractedContent()

        soup = BeautifulSoup(html, "html.parser")
        content = ExtractedContent()

        # Extract title
        content.title = self._extract_title(soup)

        # Extract meta tags
        content.meta_description = self._extract_meta(soup, "description")
        content.meta_keywords = self._extract_meta_keywords(soup)
        content.author = self._extract_meta(soup, "author")
        content.canonical_url = self._extract_canonical(soup)
        content.language = self._extract_language(soup)

        # Remove script, style, noscript and title tags (title is already
        # captured in content.title; decomposing it keeps the page title out of
        # the visible body text so it is not double-counted in word_count).
        for tag in soup(["script", "style", "noscript", "title"]):
            tag.decompose()

        # Extract headings
        content.headings = self._extract_headings(soup)

        # Extract links
        content.links = self._extract_links(soup)

        # Extract images
        content.images = self._extract_images(soup)

        # Extract text
        content.text = self._extract_text(soup)
        content.word_count = len(content.text.split())

        return content

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title, preferring og:title."""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return str(og_title["content"]).strip()
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        return ""

    def _extract_meta(self, soup: BeautifulSoup, name: str) -> str:
        """Extract meta tag content."""
        meta = soup.find("meta", attrs={"name": name})
        if meta and meta.get("content"):
            return str(meta["content"]).strip()
        return ""

    def _extract_meta_keywords(self, soup: BeautifulSoup) -> list[str]:
        """Extract meta keywords."""
        meta = soup.find("meta", attrs={"name": "keywords"})
        if meta and meta.get("content"):
            return [k.strip() for k in str(meta["content"]).split(",") if k.strip()]
        return []

    def _extract_canonical(self, soup: BeautifulSoup) -> str:
        """Extract canonical URL."""
        link = soup.find("link", rel="canonical")
        if link and link.get("href"):
            return str(link["href"]).strip()
        return ""

    def _extract_language(self, soup: BeautifulSoup) -> str:
        """Extract page language."""
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return str(html_tag["lang"]).strip()
        return ""

    def _extract_headings(self, soup: BeautifulSoup) -> list[str]:
        """Extract all heading text."""
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = tag.get_text(strip=True)
            if text:
                headings.append(text)
        return headings

    def _extract_links(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        """Extract all links as (text, url) tuples."""
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = str(a["href"]).strip()
            if href:
                links.append((text, href))
        return links

    def _extract_images(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        """Extract all images as (alt, src) tuples."""
        images = []
        for img in soup.find_all("img"):
            alt = str(img.get("alt", "")).strip()
            src = str(img.get("src", "")).strip()
            if src:
                images.append((alt, src))
        return images

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract visible text content."""
        text = soup.get_text(separator=" ", strip=True)
        # Normalize whitespace
        text = " ".join(text.split())
        if len(text) > self.max_text_length:
            text = text[: self.max_text_length]
        return text

    def extract_readability_score(self, content: ExtractedContent) -> float:
        """Compute a content richness score (0.0-1.0) from three components:
        min(word_count/500, 0.4) + min(len(headings)*0.1, 0.3) + 0.3 if
        meta_description present. Returns 0.0 if text is empty or
        word_count < 50."""
        if not content.text:
            return 0.0

        words = content.text.split()
        if len(words) < 50:
            return 0.0

        score = 0.0
        # Length score (up to 0.4)
        score += min(len(words) / 500, 0.4)
        # Headings score (up to 0.3)
        score += min(len(content.headings) * 0.1, 0.3)
        # Description score (up to 0.3)
        if content.meta_description:
            score += 0.3
        return min(score, 1.0)
