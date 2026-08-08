"""URL utility functions."""

from __future__ import annotations

from urllib.parse import urlparse, urljoin
from typing import Optional

EXCLUDED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico",
    ".css", ".js", ".pdf", ".zip", ".tar", ".gz", ".rar",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".bin", ".dmg", ".iso",
}

EXCLUDED_SCHEMES = {"javascript", "mailto", "data", "tel", "ftp"}


def is_valid_url(url: str) -> bool:
    """Check if URL is valid with http/https scheme."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def normalize_url(url: str, base_url: str = "") -> Optional[str]:
    """Normalize URL: lowercase domain, remove fragments, default ports.

    Args:
        url: The URL to normalize.
        base_url: Optional base URL to resolve relative URLs against.

    Returns:
        Normalized URL string, or None if URL is invalid.
    """
    if not url or not url.strip():
        return None
    url = url.strip()
    try:
        # Resolve relative URLs
        if base_url and not url.startswith(("http://", "https://")):
            url = urljoin(base_url, url)

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        if not parsed.netloc:
            return None

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]

        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        query = ("?" + parsed.query) if parsed.query else ""
        return f"{scheme}://{netloc}{path}{query}"
    except Exception:
        return None


def resolve_relative_url(base_url: str, relative_url: str) -> Optional[str]:
    """Resolve a relative URL against a base URL."""
    try:
        resolved = urljoin(base_url, relative_url)
        parsed = urlparse(resolved)
        if parsed.scheme not in ("http", "https"):
            return None
        return resolved
    except Exception:
        return None


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL, stripping port number."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower() if parsed.netloc else None
        if netloc:
            # Strip port number
            if ":" in netloc:
                netloc = netloc.rsplit(":", 1)[0]
        return netloc
    except Exception:
        return None


def is_excluded_url(url: str) -> bool:
    """Check if URL should be excluded from crawling."""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        if parsed.scheme in EXCLUDED_SCHEMES:
            return True
        path = parsed.path.lower()
        for ext in EXCLUDED_EXTENSIONS:
            if path.endswith(ext):
                return True
    except Exception:
        pass
    return False


def get_url_depth(url: str) -> int:
    """Get the depth of a URL path."""
    if not url:
        return 0
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return 0
        return len(path.split("/"))
    except Exception:
        return 0


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are on the same domain."""
    d1 = extract_domain(url1)
    d2 = extract_domain(url2)
    return d1 == d2
