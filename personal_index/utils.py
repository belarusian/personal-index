"""Utility functions for Personal Index."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url(url: str, base_url: str | None = None) -> str | None:
    """Normalize and validate a URL.

    Args:
        url: The URL to normalize.
        base_url: Optional base URL for resolving relative URLs.

    Returns:
        Normalized URL string, or None if invalid.
    """
    if not url:
        return None

    url = url.strip()

    # Remove fragment identifiers
    if "#" in url:
        url = url.split("#")[0]

    # Resolve relative URLs
    if base_url and not url.startswith(("http://", "https://", "ftp://")):
        url = urljoin(base_url, url)

    # Validate URL scheme
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None

    if not parsed.netloc:
        return None

    return url


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    parsed = urlparse(url)
    return parsed.hostname or ""


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    return extract_domain(url1) == extract_domain(url2)


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all links from HTML content.

    Args:
        html: Raw HTML content.
        base_url: Base URL for resolving relative links.

    Returns:
        List of normalized absolute URLs found in the HTML.
    """
    links = []
    # Match href attributes in anchor tags
    pattern = r'<a\s+[^>]*href\s*=\s*["\']([^"\']*)["\'][^>]*>'
    for match in re.finditer(pattern, html, re.IGNORECASE):
        href = match.group(1).strip()
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        normalized = normalize_url(href, base_url)
        if normalized:
            links.append(normalized)
    return links


def extract_title(html: str) -> str:
    """Extract the title from HTML content."""
    pattern = r'<title[^>]*>(.*?)</title>'
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_meta_description(html: str) -> str:
    """Extract the meta description from HTML content."""
    pattern = r'<meta[^>]*name\s*=\s*["\']description["\'][^>]*content\s*=\s*["\']([^"\']*)["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try reverse attribute order
    pattern = r'<meta[^>]*content\s*=\s*["\']([^"\']*)["\'][^>]*name\s*=\s*["\']description["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_text_content(html: str) -> str:
    """Extract plain text content from HTML, removing tags."""
    # Remove script and style elements
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    # Convert to lowercase and extract word tokens
    tokens = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', text.lower())
    return tokens


def compute_relevance_score(
    text: str,
    keywords: list[str],
    title: str = "",
    priority: int = 5,
) -> float:
    """Compute relevance score of text against keywords.

    Args:
        text: The text content to score.
        keywords: List of keywords to match against.
        title: Optional title for bonus scoring.
        priority: Interest priority (1-10).

    Returns:
        Relevance score between 0.0 and 10.0.
    """
    if not keywords or not text:
        return 0.0

    text_lower = text.lower()
    title_lower = title.lower()
    tokens = tokenize(text)
    total_tokens = max(len(tokens), 1)

    score = 0.0
    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Exact phrase match in text
        phrase_count = text_lower.count(keyword_lower)
        score += phrase_count * 2.0

        # Title match bonus
        if keyword_lower in title_lower:
            score += 5.0

        # Token-level matching
        keyword_tokens = tokenize(keyword)
        for kt in keyword_tokens:
            token_count = tokens.count(kt)
            score += token_count * 0.5

    # Normalize by priority
    score = min(score * (priority / 5.0), 10.0)
    return round(score, 4)
