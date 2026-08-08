"""Content extraction from HTML pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

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
    canonical_url: Optional[str] = None
    language: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    word_count: int = 0


class ContentExtractor:
    """Extract structured content from HTML."""

    # Tags to remove during extraction
    REMOVE_TAGS = {
        "script", "style", "nav", "footer", "header",
        "noscript", "iframe", "svg", "button", "form",
    }

    # Tags that contain meaningful content
    CONTENT_TAGS = {
        "article", "section", "main", "p", "div", "td",
        "li", "span", "h1", "h2", "h3", "h4", "h5", "h6",
        "blockquote", "pre", "code", "table",
    }

    def __init__(self, max_text_length: int = 100000):
        self.max_text_length = max_text_length

    def extract(self, html: str, base_url: str = "") -> ExtractedContent:
        """Extract content from HTML."""
        if not html:
            return ExtractedContent()

        soup = BeautifulSoup(html, "html.parser")
        content = ExtractedContent()

        # Extract title
        content.title = self._extract_title(soup)

        # Extract meta tags
        self._extract_meta(soup, content, base_url)

        # Extract headings
        content.headings = self._extract_headings(soup)

        # Extract links
        content.links = self._extract_links(soup, base_url)

        # Extract images
        content.images = self._extract_images(soup, base_url)

        # Extract main text content
        content.text = self._extract_text(soup)
        content.word_count = len(content.text.split())

        return content

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        # Try og:title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        return ""

    def _extract_meta(self, soup: BeautifulSoup, content: ExtractedContent, base_url: str) -> None:
        """Extract meta information."""
        # Description
        desc = soup.find("meta", attrs={"name": "description"})
        if not desc:
            desc = soup.find("meta", property="og:description")
        if desc and desc.get("content"):
            content.meta_description = desc["content"].strip()

        # Keywords
        keywords = soup.find("meta", attrs={"name": "keywords"})
        if keywords and keywords.get("content"):
            content.meta_keywords = [
                k.strip() for k in keywords["content"].split(",")
            ]

        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            content.canonical_url = canonical["href"]

        # Language
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            content.language = html_tag["lang"]

        # Author
        author = soup.find("meta", attrs={"name": "author"})
        if author and author.get("content"):
            content.author = author["content"].strip()

        # Published date
        for prop in ["article:published_time", "og:published_time"]:
            pub = soup.find("meta", property=prop)
            if pub and pub.get("content"):
                content.published_date = pub["content"]
                break

    def _extract_headings(self, soup: BeautifulSoup) -> list[str]:
        """Extract all headings."""
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = tag.get_text(strip=True)
            if text:
                headings.append(text)
        return headings

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
        """Extract all links as (text, url) pairs."""
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if text and href:
                links.append((text, href))
        return links[:100]  # Limit links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
        """Extract images as (alt_text, src) pairs."""
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if src:
                images.append((alt, src))
        return images[:50]  # Limit images

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content."""
        # Remove unwanted tags
        for tag in self.REMOVE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        # Try to find main content area
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if not main:
            main = soup

        # Get text
        text = main.get_text(separator=" ", strip=True)

        # Clean up whitespace
        import re
        text = re.sub(r'\s+', ' ', text).strip()

        # Limit length
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length]

        return text

    def extract_readability_score(self, content: ExtractedContent) -> float:
        """Calculate a readability score for the content."""
        if not content.text:
            return 0.0

        words = content.text.split()
        word_count = len(words)

        if word_count < 10:
            return 0.0

        # Simple readability heuristic
        avg_word_length = sum(len(w) for w in words) / word_count
        sentences = content.text.count(".") + content.text.count("!") + content.text.count("?")
        avg_sentence_length = word_count / max(sentences, 1)

        # Score based on content quality indicators
        score = 0.0
        if word_count > 100:
            score += 0.3
        if word_count > 500:
            score += 0.2
        if avg_word_length > 3 and avg_word_length < 8:
            score += 0.2
        if avg_sentence_length > 5 and avg_sentence_length < 30:
            score += 0.15
        if content.headings:
            score += 0.1
        if content.meta_description:
            score += 0.05

        return min(score, 1.0)
