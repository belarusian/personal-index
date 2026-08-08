"""URL utility functions for the personal index."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urljoin, urlunparse

# Common file extensions to exclude from crawling
EXCLUDED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico",
    ".css", ".js", ".pdf", ".zip", ".tar", ".gz", ".rar",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".bin", ".dmg", ".iso",
}

EXCLUDED_SCHEMES = {"javascript", "mailto", "data", "tel", "ftp"}


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid and has an http/https scheme."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize URL: lowercase scheme/domain, remove fragments."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]
        path = parsed.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        normalized = urlunparse(
            (scheme, netloc, path, parsed.params, parsed.query, "")
        )
        return normalized
    except Exception:
        return url


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def extract_subdomain(url: str) -> str:
    """Extract subdomain from URL."""
    domain = extract_domain(url)
    if not domain:
        return ""
    parts = domain.split(".")
    if len(parts) <= 2:
        return ""
    return ".".join(parts[:-2])


def get_tld(url: str) -> str:
    """Extract top-level domain from URL."""
    domain = extract_domain(url)
    if not domain:
        return ""
    parts = domain.split(".")
    return parts[-1] if parts else ""


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are on the same domain."""
    return extract_domain(url1) == extract_domain(url2)


def is_internal_link(url: str, base_url: str) -> bool:
    """Check if URL is an internal link relative to base URL."""
    return is_same_domain(url, base_url)


def remove_query_params(url: str, params: list = None) -> str:
    """Remove specific query parameters from URL."""
    if not params:
        return url
    try:
        parsed = urlparse(url)
        query_parts = parsed.query.split("&")
        filtered = [
            p for p in query_parts
            if not any(p.startswith(f"{param}=") for param in params)
        ]
        new_query = "&".join(filtered)
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
    except Exception:
        return url


def url_to_path(url: str) -> str:
    """Convert URL to a filesystem-safe path."""
    if not url:
        return ""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", path)
    return f"{parsed.netloc}_{safe}"


def join_urls(base: str, relative: str) -> str:
    """Join a base URL with a relative URL."""
    return urljoin(base, relative)


def extract_all_urls(html: str, base_url: str) -> list:
    """Extract all URLs from HTML content."""
    from bs4 import BeautifulSoup
    urls = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.startswith("javascript:"):
                continue
            full_url = urljoin(base_url, href)
            normalized = normalize_url(full_url)
            if is_valid_url(normalized):
                urls.append(normalized)
    except Exception:
        pass
    return urls


def is_robotstxt(url: str) -> bool:
    """Check if URL is a robots.txt file."""
    parsed = urlparse(url)
    return parsed.path.rstrip("/") == "/robots.txt"


def is_sitemap(url: str) -> bool:
    """Check if URL is a sitemap file."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    return "sitemap" in path


def is_excluded_url(url: str) -> bool:
    """Check if URL should be excluded from crawling."""
    if not url:
        return True
    parsed = urlparse(url)
    if parsed.scheme in EXCLUDED_SCHEMES:
        return True
    path = parsed.path.lower()
    for ext in EXCLUDED_EXTENSIONS:
        if path.endswith(ext):
            return True
    return False
