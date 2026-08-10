"""HTML page scraper with content extraction."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration for HTML scraping."""

    extract_meta: bool = True
    extract_links: bool = True
    extract_images: bool = True
    extract_headings: bool = True
    extract_tables: bool = False
    remove_scripts: bool = True
    max_content_length: int = 1_000_000
    blocked_tags: list[str] = field(default_factory=lambda: ["script", "style", "noscript"])


@dataclass
class ScrapedContent:
    """Content extracted from an HTML page."""

    url: str = ""
    title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    headings: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    raw_text: str = ""
    word_count: int = 0
    charset: str = "utf-8"


class HTMLScraper:
    """Scraps HTML content and extracts structured data."""

    def __init__(self, config: ScraperConfig | None = None):
        self.config = config or ScraperConfig()

    def scrape(self, html: str, base_url: str = "") -> ScrapedContent:
        """Scrape HTML content and return structured data."""
        soup = BeautifulSoup(html, "html.parser")
        result = ScrapedContent(url=base_url)

        self._extract_charset(soup, result)
        self._clean_page(soup)

        if self.config.extract_meta:
            self._extract_meta_tags(soup, result)

        if self.config.extract_headings:
            self._extract_headings(soup, result)

        self._extract_paragraphs(soup, result)

        if self.config.extract_links:
            self._extract_links(soup, result, base_url)

        if self.config.extract_images:
            self._extract_images(soup, result, base_url)

        if self.config.extract_tables:
            self._extract_tables(soup, result)

        result.raw_text = self._get_clean_text(soup)
        result.word_count = len(result.raw_text.split())

        if len(result.raw_text) > self.config.max_content_length:
            result.raw_text = result.raw_text[: self.config.max_content_length]

        return result

    def _extract_charset(self, soup: BeautifulSoup, result: ScrapedContent) -> None:
        meta_charset = soup.find("meta", attrs={"charset": True})
        if meta_charset:
            result.charset = meta_charset.get("charset", "utf-8")  # type: ignore[assignment]
        meta_http = soup.find("meta", attrs={"http-equiv": "Content-Type"})
        if meta_http and meta_http.get("content"):
            match = re.search(r"charset=([^\s;]+)", str(meta_http["content"]))  # type: ignore[misc]
            if match:
                result.charset = match.group(1)

    def _clean_page(self, soup: BeautifulSoup) -> None:
        for tag_name in self.config.blocked_tags:
            for tag in soup.find_all(tag_name):
                tag.decompose()

    def _extract_meta_tags(self, soup: BeautifulSoup, result: ScrapedContent) -> None:
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title_str = str(title_tag.string) if title_tag.string else ""
            result.title = title_str.strip()  # type: ignore[misc]

        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"):
            result.meta_description = str(desc_tag["content"]).strip()  # type: ignore[misc]

        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag and keywords_tag.get("content"):
            result.meta_keywords = str(keywords_tag["content"]).strip()  # type: ignore[misc]

        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content") and not result.title:
            result.title = str(og_title["content"]).strip()  # type: ignore[misc]

        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content") and not result.meta_description:
            result.meta_description = str(og_desc["content"]).strip()  # type: ignore[misc]

    def _extract_headings(self, soup: BeautifulSoup, result: ScrapedContent) -> None:
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text(strip=True)
                if text:
                    result.headings.append(f"h{level}: {text}")

    def _extract_paragraphs(self, soup: BeautifulSoup, result: ScrapedContent) -> None:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                result.paragraphs.append(text)

    def _extract_links(self, soup: BeautifulSoup, result: ScrapedContent, base_url: str) -> None:
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()  # type: ignore[misc]
            if not href:
                continue
            absolute = urljoin(base_url, str(href))  # type: ignore[misc]
            if absolute in seen:
                continue
            seen.add(absolute)
            text = a.get_text(strip=True)
            result.links.append({
                "url": absolute,
                "text": text,
                "title": a.get("title", ""),
            })

    def _extract_images(self, soup: BeautifulSoup, result: ScrapedContent, base_url: str) -> None:
        for img in soup.find_all("img"):
            src = str(img.get("src", ""))  # type: ignore[misc]
            if not src:
                continue
            absolute = urljoin(base_url, str(src))  # type: ignore[misc]
            result.images.append({
                "src": absolute,
                "alt": img.get("alt", ""),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
            })

    def _extract_tables(self, soup: BeautifulSoup, result: ScrapedContent) -> None:
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = []
                for td in tr.find_all(["td", "th"]):
                    cells.append(td.get_text(strip=True))
                if cells:
                    rows.append(cells)
            if rows:
                result.tables.append({"rows": rows})

    def _get_clean_text(self, soup: BeautifulSoup) -> str:
        text_parts = []
        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th"]):
            text = element.get_text(strip=True)
            if text:
                text_parts.append(text)
        return " ".join(text_parts)
