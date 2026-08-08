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


def normalize_url(url: str) -> str:
    """Normalize URL: lowercase domain, remove fragments."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        query = ("?" + parsed.query) if parsed.query else ""
        return f"{scheme}://{netloc}{path}{query}"
    except Exception:
        return url


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
    """Extract domain from URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() if parsed.netloc else None
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
