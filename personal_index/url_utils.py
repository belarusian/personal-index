"""URL utilities for parsing, validation, and normalization."""

import re
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode
from typing import Optional, Set


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments, trailing slashes, and standardizing."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower().rstrip(":"),
        path,
        parsed.params,
        parsed.query,
        "",  # Remove fragment
    ))
    # Remove default ports
    if parsed.port in (80, 443):
        host = parsed.hostname
        normalized = urlunparse((
            parsed.scheme.lower(),
            host,
            path,
            parsed.params,
            parsed.query,
            "",
        ))
    return normalized


def extract_links(html: str, base_url: str) -> list:
    """Extract all links from HTML content."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        absolute_url = urljoin(base_url, href)
        if is_valid_url(absolute_url):
            links.append(normalize_url(absolute_url))
    return list(set(links))


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def url_matches_pattern(url: str, pattern: str) -> bool:
    """Check if URL matches a given pattern (supports wildcards)."""
    regex_pattern = "^" + re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".") + "$"
    return bool(re.match(regex_pattern, url, re.IGNORECASE))


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    return get_domain(url1) == get_domain(url2)


def get_url_depth(url: str, seed_url: str) -> int:
    """Calculate the depth of a URL relative to a seed URL."""
    seed_parsed = urlparse(seed_url)
    url_parsed = urlparse(url)
    seed_path_parts = [p for p in seed_parsed.path.split("/") if p]
    url_path_parts = [p for p in url_parsed.path.split("/") if p]
    if not is_same_domain(url, seed_url):
        return -1
    return len(url_path_parts) - len(seed_path_parts)


def filter_urls(
    urls: list,
    allowed_extensions: Optional[list] = None,
    blocked_domains: Optional[Set[str]] = None,
    url_patterns: Optional[list] = None,
) -> list:
    """Filter URLs based on criteria."""
    filtered = []
    for url in urls:
        if blocked_domains and get_domain(url) in blocked_domains:
            continue
        if allowed_extensions:
            parsed = urlparse(url)
            ext = ""
            if "." in parsed.path:
                ext = "." + parsed.path.rsplit(".", 1)[-1].lower()
            if ext not in allowed_extensions and ext != "":
                if parsed.path.endswith(allowed_extensions):
                    filtered.append(url)
                continue
        if url_patterns:
            if not any(url_matches_pattern(url, p) for p in url_patterns):
                continue
        filtered.append(url)
    return filtered
