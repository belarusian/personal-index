"""Text processing utilities."""

from __future__ import annotations

import re
from typing import List, Optional

from bs4 import BeautifulSoup

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "that", "this", "these",
    "those", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "he", "him", "his", "she", "her", "they", "them", "their", "what",
    "which", "who", "whom", "am", "about", "up", "down",
}


def extract_text_from_html(html: Optional[str]) -> str:
    """Extract visible text from HTML, removing scripts and styles."""
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())
    except Exception:
        return ""


def extract_title_from_html(html: Optional[str]) -> str:
    """Extract page title from HTML."""
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        if title and title.string:
            return title.string.strip()
        return ""
    except Exception:
        return ""


def extract_meta_description(html: Optional[str]) -> str:
    """Extract meta description from HTML."""
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        return ""
    except Exception:
        return ""


def tokenize(text: Optional[str]) -> List[str]:
    """Tokenize text into lowercase words, filtering stopwords."""
    if not text:
        return []
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def generate_snippet(
    text: str, query: str, max_length: int = 200
) -> str:
    """Generate a snippet highlighting query terms."""
    if not text:
        return ""
    query_lower = query.lower()
    idx = text.lower().find(query_lower)
    if idx == -1:
        return text[:max_length] + (
            "..." if len(text) > max_length else ""
        )
    start = max(0, idx - 50)
    end = min(len(text), idx + len(query) + max_length)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def compute_text_similarity(text1: str, text2: str) -> float:
    """Compute similarity between two texts based on shared tokens."""
    tokens1 = set(tokenize(text1))
    tokens2 = set(tokenize(text2))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text at word boundary."""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.5:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "..."


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())


def extract_links_from_html(html: str, base_url: str = "") -> List[str]:
    """Extract all links from HTML, resolving against base_url.

    Excludes javascript:, mailto:, and hash-only links.
    """
    if not html:
        return []
    try:
        from urllib.parse import urljoin
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Skip hash-only links
            if href.startswith("#"):
                continue
            # Skip javascript and mailto
            if href.startswith(("javascript:", "mailto:", "data:", "tel:")):
                continue
            # Resolve relative URLs
            if base_url:
                full_url = urljoin(base_url, href)
            else:
                full_url = href
            links.append(full_url)
        return links
    except Exception:
        return []
