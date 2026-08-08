"""URL utility functions for parsing, validation, and normalization."""

import re
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional


# Common patterns to exclude from crawling
EXCLUDED_PATHS = [
    r"\.css$",
    r"\.js$",
    r"\.png$",
    r"\.jpg$",
    r"\.jpeg$",
    r"\.gif$",
    r"\.svg$",
    r"\.ico$",
    r"\.pdf$",
    r"\.zip$",
    r"\.tar$",
    r"\.gz$",
    r"\.mp3$",
    r"\.mp4$",
    r"\.avi$",
    r"\.exe$",
    r"\.doc$",
    r"\.docx$",
    r"\.xls$",
    r"\.xlsx$",
]

# Build compiled pattern for excluded paths
_EXCLUDED_PATTERN = re.compile("|".join(EXCLUDED_PATHS), re.IGNORECASE)


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL.

    Args:
        url: URL string to validate.

    Returns:
        True if the URL is valid.
    """
    try:
        parsed = urlparse(url)
        return all([
            parsed.scheme in ("http", "https"),
            parsed.netloc,
        ])
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments and trailing slashes.

    Args:
        url: URL to normalize.

    Returns:
        Normalized URL string.
    """
    parsed = urlparse(url)
    # Remove fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        parsed.params,
        parsed.query,
        "",  # No fragment
    ))
    return normalized


def resolve_relative_url(base_url: str, relative_url: str) -> Optional[str]:
    """Resolve a relative URL against a base URL.

    Args:
        base_url: The base URL.
        relative_url: The relative URL to resolve.

    Returns:
        Absolute URL or None if invalid.
    """
    try:
        resolved = urljoin(base_url, relative_url)
        if is_valid_url(resolved):
            return normalize_url(resolved)
    except Exception:
        pass
    return None


def extract_domain(url: str) -> Optional[str]:
    """Extract the domain from a URL.

    Args:
        url: URL to extract domain from.

    Returns:
        Domain string or None.
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() if parsed.netloc else None
    except Exception:
        return None


def is_excluded_url(url: str) -> bool:
    """Check if a URL should be excluded from crawling.

    Args:
        url: URL to check.

    Returns:
        True if the URL should be excluded.
    """
    if _EXCLUDED_PATTERN.search(url):
        return True

    # Exclude javascript: and data: URLs
    parsed = urlparse(url)
    if parsed.scheme in ("javascript", "data", "mailto", "tel"):
        return True

    return False


def get_url_depth(url: str, seed_domain: Optional[str] = None) -> int:
    """Estimate the depth of a URL based on path segments.

    Args:
        url: URL to analyze.
        seed_domain: Optional seed domain for relative depth.

    Returns:
        Depth level (number of path segments).
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return 0
    return len(path.split("/"))


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain.

    Args:
        url1: First URL.
        url2: Second URL.

    Returns:
        True if both URLs share the same domain.
    """
    domain1 = extract_domain(url1)
    domain2 = extract_domain(url2)
    return domain1 == domain2 and domain1 is not None
