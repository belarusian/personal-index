"""
URL utilities for personal-index.

Provides URL validation, normalization, and classification.
"""

import re
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments, trailing slashes, etc."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
        # Remove fragment
        path = parsed.path.rstrip("/") or "/"
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            parsed.query,
            "",  # No fragment
        ))
        return normalized
    except Exception:
        return url


def get_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def get_base_url(url: str) -> str:
    """Get the base URL (scheme + domain) from a URL."""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return ""


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are from the same domain."""
    return get_domain(url1) == get_domain(url2)


def is_external_link(url: str, base_url: str) -> bool:
    """Check if a URL is external to the base domain."""
    return not is_same_domain(url, base_url)


def resolve_url(url: str, base_url: str) -> str:
    """Resolve a relative URL against a base URL."""
    if not url:
        return base_url
    if url.startswith(("http://", "https://")):
        return normalize_url(url)
    return normalize_url(urljoin(base_url, url))


def is_crawlable_url(url: str) -> bool:
    """Check if a URL is suitable for crawling."""
    if not is_valid_url(url):
        return False
    parsed = urlparse(url)
    # Skip non-HTTP URLs
    if parsed.scheme not in ("http", "https"):
        return False
    # Skip mailto, tel, javascript
    if url.startswith(("mailto:", "tel:", "javascript:", "data:", "ftp:")):
        return False
    # Skip fragment-only URLs
    if not parsed.path and not parsed.query:
        return False
    return True


def is_resource_url(url: str) -> bool:
    """Check if a URL points to a static resource (image, CSS, JS, etc.)."""
    resource_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp',
        '.css', '.js', '.woff', '.woff2', '.ttf', '.eot', '.otf',
        '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.apk', '.exe', '.dmg', '.iso',
    }
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    for ext in resource_extensions:
        if path_lower.endswith(ext):
            return True
    # Check content-type-like patterns in URL
    if any(ext in path_lower for ext in ['.json', '.xml', '.rss', '.atom']):
        return False  # These are crawlable
    return False


def classify_url(url: str) -> str:
    """Classify a URL by type."""
    if not is_valid_url(url):
        return "invalid"
    if is_resource_url(url):
        return "resource"
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith(('.html', '.htm')) or path == '/':
        return "page"
    if any(ext in path for ext in ['.json', '.xml', '.rss', '.atom']):
        return "feed"
    return "page"  # Default classification


def extract_path_segments(url: str) -> list[str]:
    """Extract path segments from a URL."""
    try:
        parsed = urlparse(url)
        segments = [s for s in parsed.path.split("/") if s]
        return segments
    except Exception:
        return []


def url_depth(url: str) -> int:
    """Get the depth of a URL path."""
    return len(extract_path_segments(url))


def is_well_known(url: str) -> bool:
    """Check if a URL is a well-known path (robots.txt, sitemap.xml, etc.)."""
    well_known = {
        '/robots.txt',
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/.well-known/',
        '/favicon.ico',
    }
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    for wk in well_known:
        if path == wk or path.startswith(wk):
            return True
    return False


def generate_sitemap_url(url: str) -> str:
    """Generate a sitemap URL from a base URL."""
    base = get_base_url(url)
    return f"{base}/sitemap.xml"


# Alias for backward compatibility
extract_domain = get_domain


def is_internal_link(url: str, base_url: str) -> bool:
    """Check if a URL is internal to the base domain."""
    return is_same_domain(url, base_url)


def sanitize_url(url: str) -> str:
    """Sanitize a URL by removing dangerous components."""
    if not url:
        return url
    # Remove fragments
    if "#" in url:
        url = url.split("#")[0]
    # Remove query parameters that could be dangerous
    parsed = urlparse(url)
    # Normalize
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path,
        parsed.params,
        parsed.query,
        "",
    ))


def url_to_path(url: str) -> str:
    """Convert a URL to a safe filesystem path."""
    import hashlib
    # Use hash of URL as filename to avoid path issues
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"pages/{url_hash}.html"


def generate_seed_urls(topics: list[str], max_per_topic: int = 5) -> list[str]:
    """Generate seed URLs for given topics using a search engine."""
    # Simple implementation: generate Wikipedia URLs for topics
    urls = []
    for topic in topics:
        # Wikipedia as a seed source
        wiki_url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
        urls.append(wiki_url)
    return urls[:max_per_topic * len(topics)]
