"""Utilities package."""

# Re-export from root url_utils for backward compatibility
from personal_index.url_utils import (
    is_valid_url,
    normalize_url,
    resolve_relative_url,
    extract_domain,
    is_excluded_url,
    get_url_depth,
    is_same_domain,
    EXCLUDED_EXTENSIONS,
    EXCLUDED_SCHEMES,
)

import re
from bs4 import BeautifulSoup


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all valid links from HTML content."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Skip javascript, mailto, etc.
        if href.startswith(("javascript:", "mailto:", "data:", "tel:")):
            continue
        # Resolve relative URLs
        from personal_index.url_utils import resolve_relative_url
        resolved = resolve_relative_url(base_url, href)
        if resolved:
            links.append(resolved)
    return links


def extract_title(html: str) -> str:
    """Extract page title from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    return ""


def extract_meta_description(html: str) -> str:
    """Extract meta description from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return ""


def extract_text_content(html: str) -> str:
    """Extract text content from HTML, removing scripts and styles."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    # Normalize whitespace
    return re.sub(r'\s+', ' ', text).strip()


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    if not text:
        return []
    return re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', text.lower())


def compute_relevance_score(
    text: str,
    keywords: list[str],
    title: str = "",
    priority: int = 5,
) -> float:
    """Compute relevance score of text against keywords."""
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    title_lower = title.lower()
    total = 0.0
    for kw in keywords:
        kw_lower = kw.lower()
        # Content matches
        content_count = text_lower.count(kw_lower)
        total += content_count
        # Title matches get bonus
        title_count = title_lower.count(kw_lower)
        total += title_count * 2
    return min(total * priority / 10.0, priority * 10.0)


__all__ = [
    "is_valid_url",
    "normalize_url",
    "resolve_relative_url",
    "extract_domain",
    "is_excluded_url",
    "get_url_depth",
    "is_same_domain",
    "extract_links",
    "extract_title",
    "extract_meta_description",
    "extract_text_content",
    "tokenize",
    "compute_relevance_score",
    "EXCLUDED_EXTENSIONS",
    "EXCLUDED_SCHEMES",
]
