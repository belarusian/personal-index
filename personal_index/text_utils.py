"""
Text utilities for personal-index.

Provides text extraction, normalization, and snippet generation.
"""

import re
import html
from typing import Optional


def extract_text_from_html(html_content: str) -> str:
    """Extract clean text content from HTML."""
    if not html_content:
        return ""

    # Remove script and style elements
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_content, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<noscript[^>]*>.*?</noscript>', ' ', text, flags=re.IGNORECASE | re.DOTALL)

    # Handle common block elements
    text = re.sub(r'</?(p|div|article|section|header|footer|nav|main|aside|blockquote|pre|ul|ol|li|h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(br|hr)[^>]*>/', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</?(span|strong|em|b|i|u|a)[^>]*>', ' ', text, flags=re.IGNORECASE)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Decode HTML entities
    text = html.unescape(text)

    # Clean whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_title_from_html(html_content: str) -> str:
    """Extract the title from HTML."""
    if not html_content:
        return ""
    match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if match:
        return html.unescape(match.group(1).strip())
    return ""


def extract_meta_description(html_content: str) -> str:
    """Extract meta description from HTML."""
    if not html_content:
        return ""
    match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
    if not match:
        match = re.search(r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', html_content, re.IGNORECASE)
    if match:
        return html.unescape(match.group(1).strip())
    return ""


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, filtering stopwords."""
    if not text:
        return []
    STOPWORDS = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'it', 'as', 'was', 'are', 'be',
        'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they',
        'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
        'not', 'no', 'do', 'does', 'did', 'has', 'have', 'had', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'shall', 'been', 'being',
        'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
        'about', 'up', 'out', 'if', 'then', 'else', 'into', 'over', 'after',
        'before', 'between', 'under', 'again', 'further', 'here', 'there',
    }
    words = re.findall(r'\b[a-z0-9]+\b', text.lower())
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]


def generate_snippet(text: str, query: str, max_length: int = 200) -> str:
    """Generate a search snippet highlighting query terms."""
    if not text:
        return ""

    query_terms = tokenize(query)
    if not query_terms:
        return text[:max_length]

    text_lower = text.lower()

    # Find the best context around query terms
    best_start = 0
    best_score = -1

    for term in query_terms:
        idx = text_lower.find(term)
        if idx != -1:
            score = len(term)
            if score > best_score:
                best_score = score
                best_start = max(0, idx - 50)

    snippet = text[best_start:best_start + max_length]
    if len(snippet) < len(text):
        snippet = "..." + snippet
    if best_start > 0:
        snippet = snippet + "..."

    return snippet


def compute_text_similarity(text1: str, text2: str) -> float:
    """Compute simple text similarity using word overlap."""
    words1 = set(tokenize(text1))
    words2 = set(tokenize(text2))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to a maximum length, preserving word boundaries."""
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0
    return len(re.findall(r'\b\w+\b', text))


def extract_links_from_html(html_content: str, base_url: str) -> list[str]:
    """Extract all valid links from HTML content."""
    links = []
    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
    for match in re.finditer(pattern, html_content, re.IGNORECASE):
        href = match.group(1).strip()
        if href.startswith(('http://', 'https://')):
            from urllib.parse import urlparse
            parsed = urlparse(href)
            if parsed.netloc:
                links.append(href)
        elif href.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
        elif not href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            from urllib.parse import urljoin
            links.append(urljoin(base_url, href))
    return links
