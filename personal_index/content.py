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
            # Extract words from headings
            words = re.findall(r'[a-z0-9]+', heading.lower())
            keywords.extend(words)
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


def extract_content(
    html: str,
    url: str,
    status_code: int = 200,
) -> ExtractedContent:
    """Extract structured content from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()

    # Extract meta description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = str(meta_tag["content"]).strip()

    # Extract meta keywords
    meta_keywords = []
    meta_kw_tag = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw_tag and meta_kw_tag.get("content"):
        meta_keywords = [
            kw.strip() for kw in str(meta_kw_tag["content"]).split(",") if kw.strip()
        ]

    # Extract headings
    headings = []
    for level in range(1, 4):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            if text:
                headings.append(f"h{level}: {text}")

    # Remove scripts and styles
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Extract text
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()

    # Extract links
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag["href"])
        if not href.startswith(("javascript:", "mailto:", "data:", "tel:")):
            from personal_index.url_utils import resolve_relative_url
            resolved = resolve_relative_url(url, href)
            if resolved:
                links.append(resolved)

    # Detect language
    language = "en"
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        language = str(html_tag["lang"]).split("-")[0]

    return ExtractedContent(
        url=url,
        title=title,
        text=text,
        meta_description=meta_desc,
        meta_keywords=meta_keywords,
        headings=headings,
        links=links,
        content_length=len(text),
        language=language,
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
