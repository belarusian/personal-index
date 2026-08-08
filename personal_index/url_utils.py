"""URL utilities for validation, normalization, and extraction."""

from __future__ import annotations

import re
from urllib.parse import (
    parse_qs,
    quote,
    unquote,
    urlparse,
    urlunparse,
)


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments, normalizing case, etc."""
    try:
        parsed = urlparse(url)
        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        # Normalize path
        path = parsed.path
        # Remove trailing slash (except for root)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        # Remove default ports
        if ":" in netloc:
            host, port = netloc.rsplit(":", 1)
            if (scheme == "http" and port == "80") or \
               (scheme == "https" and port == "443"):
                netloc = host
        # Remove fragment
        return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))
    except Exception:
        return url


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    return extract_domain(url1) == extract_domain(url2)


def extract_subdomain(url: str) -> str:
    """Extract the subdomain from a URL."""
    domain = extract_domain(url)
    parts = domain.split(".")
    if len(parts) > 2:
        return ".".join(parts[:-2])
    return ""


def get_tld(url: str) -> str:
    """Get the top-level domain from a URL."""
    domain = extract_domain(url)
    parts = domain.split(".")
    if parts:
        return parts[-1]
    return ""


def is_internal_link(url: str, base_url: str) -> bool:
    """Check if a URL is an internal link relative to a base URL."""
    return is_same_domain(url, base_url)


def remove_query_params(url: str, params: list[str] | None = None) -> str:
    """Remove specific query parameters from a URL."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if params:
        for param in params:
            query.pop(param, None)
    # Rebuild query string
    new_query = "&".join(
        f"{k}={v[0]}" for k, v in sorted(query.items())
    )
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


def url_to_path(url: str) -> str:
    """Convert a URL to a safe filesystem path."""
    parsed = urlparse(url)
    # Replace special characters
    safe_path = re.sub(r'[<>:"/\\|?*]', '_', parsed.path)
    # Ensure non-empty
    if not safe_path or safe_path == "_":
        safe_path = "index"
    return f"{parsed.netloc}{safe_path}"


def join_urls(base: str, relative: str) -> str:
    """Join a base URL with a relative URL."""
    from urllib.parse import urljoin
    return urljoin(base, relative)


def extract_all_urls(text: str) -> list[str]:
    """Extract all URLs from text."""
    url_pattern = r'https?://[^\s<>"\')\]]+'
    urls = re.findall(url_pattern, text)
    return [normalize_url(u) for u in urls if is_valid_url(u)]


def is_robotstxt(url: str) -> bool:
    """Check if URL points to a robots.txt file."""
    parsed = urlparse(url)
    return parsed.path.lower() == "/robots.txt"


def is_sitemap(url: str) -> bool:
    """Check if URL points to a sitemap."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    return "sitemap" in path_lower or path_lower.endswith(".xml")
