"""URL utilities for personal-index.

Provides URL normalization, validation, and domain extraction.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent comparison and storage.

    - Removes fragments
    - Lowercases the scheme and netloc
    - Removes trailing slashes (except for root)
    - Sorts query parameters for consistency

    Args:
        url: URL to normalize.

    Returns:
        Normalized URL string.
    """
    parsed = urlparse(url)

    # Lowercase scheme and netloc
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",  # Remove fragment
    )

    # Remove trailing slash (except for root path)
    path = normalized.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    normalized = normalized._replace(path=path)

    return urlunparse(normalized)


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL.

    Args:
        url: URL string to validate.

    Returns:
        True if the URL is valid.
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def extract_domain(url: str) -> str:
    """Extract the domain from a URL.

    Args:
        url: URL string.

    Returns:
        Domain string (e.g., 'example.com').
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are on the same domain.

    Args:
        url1: First URL.
        url2: Second URL.

    Returns:
        True if both URLs share the same domain.
    """
    return extract_domain(url1) == extract_domain(url2)


def is_internal_link(url: str, base_url: str) -> bool:
    """Check if a URL is an internal link relative to a base URL.

    Args:
        url: URL to check.
        base_url: Base URL for comparison.

    Returns:
        True if the URL is on the same domain as the base URL.
    """
    return is_same_domain(url, base_url)


def sanitize_url(url: str) -> str:
    """Sanitize a URL by removing potentially dangerous components.

    - Removes fragments
    - Removes encoded null bytes
    - Normalizes whitespace

    Args:
        url: URL to sanitize.

    Returns:
        Sanitized URL string.
    """
    # Remove fragments
    if "#" in url:
        url = url.split("#")[0]

    # Remove encoded null bytes
    url = url.replace("%00", "").replace("\x00", "")

    # Normalize whitespace
    url = " ".join(url.split()).strip()

    return url


def url_to_path(url: str) -> str:
    """Convert a URL to a safe filesystem path.

    Args:
        url: URL to convert.

    Returns:
        Safe filesystem path string.
    """
    parsed = urlparse(url)
    # Replace unsafe characters
    safe_path = re.sub(r"[^a-zA-Z0-9._-]", "_", parsed.path)
    if not safe_path or safe_path == "_":
        safe_path = "index"
    return f"{parsed.netloc}/{safe_path}"


def generate_seed_urls(
    keywords: list[str],
    search_engine: str = "google",
) -> list[str]:
    """Generate seed URLs from keywords using a search engine.

    Args:
        keywords: List of keywords to search for.
        search_engine: Search engine to use ('google', 'duckduckgo', 'bing').

    Returns:
        List of search result URLs to use as seed URLs.
    """
    query = "+".join(keywords)

    engines = {
        "google": f"https://www.google.com/search?q={query}",
        "duckduckgo": f"https://duckduckgo.com/?q={query}",
        "bing": f"https://www.bing.com/search?q={query}",
    }

    return [engines.get(search_engine, engines["google"])]
