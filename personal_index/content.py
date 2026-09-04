"""Content extraction and text processing for personal-index."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ExtractedContent:
    """Content extracted from a web page."""
    url: str
    title: str = ""
    text: str = ""
    meta_description: str = ""
    meta_keywords: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    content_length: int = 0
    language: str = "en"
    status_code: int = 200

    def get_searchable_text(self) -> str:
        """Get combined searchable text from title, headings, and body."""
        parts = [self.title] + self.headings + [self.text]
        return " ".join(p for p in parts if p)

    def get_keywords(self) -> list[str]:
        """Extract keywords from meta keywords and headings."""
        keywords = list(self.meta_keywords)
        for heading in self.headings:
            # Strip the "hN:" level prefix so only the heading text
            # contributes keywords (the marker itself is not a keyword).
            text = re.sub(r'^h\d+:\s*', '', heading)
            words = re.findall(r'[a-z0-9]+', text.lower())
            # Filter out stopwords so only meaningful terms are keywords
            # (meta keywords are author-supplied and kept as-is).
            keywords.extend(remove_stopwords(words))
        return list(set(keywords))


# Common English stopwords
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "what", "which", "who", "whom", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "about", "above", "after", "again", "also", "any",
    "because", "before", "between", "during", "if", "into", "like", "new",
    "now", "old", "over", "then", "there", "here", "up", "out", "off",
}


def _extract_title(soup: BeautifulSoup) -> str:
    tag = soup.find("title")
    return tag.string.strip() if tag and tag.string else ""


def _extract_meta_desc(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    return str(tag["content"]).strip() if tag and tag.get("content") else ""


def _extract_meta_keywords(soup: BeautifulSoup) -> list[str]:
    tag = soup.find("meta", attrs={"name": "keywords"})
    if tag and tag.get("content"):
        return [kw.strip() for kw in str(tag["content"]).split(",") if kw.strip()]
    return []


def _extract_headings(soup: BeautifulSoup) -> list[str]:
    headings: list[str] = []
    for level in range(1, 4):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            if text:
                headings.append(f"h{level}: {text}")
    return headings


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return re.sub(r'\s+', ' ', soup.get_text(separator=" ")).strip()


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    from personal_index.url_utils import resolve_relative_url
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if href and not href.startswith(("javascript:", "mailto:", "data:", "tel:")):
            resolved = resolve_relative_url(base_url, href)
            if resolved:
                links.append(resolved)
    return links


def _detect_language(soup: BeautifulSoup) -> str:
    html_tag = soup.find("html")
    return str(html_tag["lang"]).split("-")[0] if html_tag and html_tag.get("lang") else "en"


def extract_content(
    html: str,
    url: str,
    status_code: int = 200,
) -> ExtractedContent:
    """Extract structured content from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    text = _extract_text(soup)
    return ExtractedContent(
        url=url, title=_extract_title(soup), text=text,
        meta_description=_extract_meta_desc(soup),
        meta_keywords=_extract_meta_keywords(soup),
        headings=_extract_headings(soup), links=_extract_links(soup, url),
        content_length=len(text), language=_detect_language(soup),
        status_code=status_code,
    )


def remove_stopwords(
    tokens: list[str],
    stopwords: set[str] | None = None,
) -> list[str]:
    """Remove stopwords from token list."""
    if not tokens:
        return []
    stop = stopwords or STOPWORDS
    return [t for t in tokens if t not in stop]


def compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency for a list of tokens."""
    if not tokens:
        return {}
    freq: dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    total = len(tokens)
    return {token: count / total for token, count in freq.items()}
