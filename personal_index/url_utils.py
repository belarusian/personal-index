"""URL utility functions for the personal index.

Merged from url_utils.py and url_normalizer.py.
"""

from __future__ import annotations

import re
from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

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
    except (ValueError, AttributeError):
        return False


def _normalize_path(path: str, lowercase: bool) -> str:
    p = path.lower() if lowercase else path
    p = re.sub(r"/+", "/", p)
    if p != "/" and p.endswith("/"):
        p = p.rstrip("/")
    return p

def _normalize_query(query: str, sort: bool) -> str:
    if not sort or not query:
        return query
    params = parse_qs(query, keep_blank_values=True)
    sorted_params = dict(sorted(params.items()))
    return urlencode(sorted_params, doseq=True)

def normalize_url(
    url: str,
    base_url: str = "",
    remove_fragment: bool = True,
    lowercase_path: bool = True,
    remove_default_port: bool = True,
    sort_query_params: bool = True,
) -> str | None:
    """Normalize a URL by applying standard transformations."""
    if not url:
        return None
    try:
        if base_url and not url.startswith(("http://", "https://")):
            url = urljoin(base_url, url)
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if remove_default_port:
            netloc = _remove_default_port(netloc, scheme)
        path = _normalize_path(parsed.path, lowercase_path)
        query = _normalize_query(parsed.query, sort_query_params)
        fragment = "" if remove_fragment else parsed.fragment
        if scheme not in ("http", "https"):
            return None
        return urlunparse((scheme, netloc, path, "", query, fragment))
    except (ValueError, AttributeError):
        return url


def _remove_default_port(netloc: str, scheme: str) -> str:
    """Remove default port from netloc."""
    default_ports = {"http": 80, "https": 443, "ftp": 21}
    default_port = default_ports.get(scheme)
    if default_port is None:
        return netloc

    if ":" in netloc:
        host, port_str = netloc.rsplit(":", 1)
        try:
            port = int(port_str)
            if port == default_port:
                return host
        except ValueError:
            pass
    return netloc


def is_canonical(url: str) -> bool:
    """Check if a URL is already in canonical form."""
    return normalize_url(url) == url


def extract_domain(url: str) -> str | None:
    """Extract domain from URL, stripping port number."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
        netloc = parsed.netloc.lower()
        # Strip port number. A bracketed IPv6 literal (e.g. "[::1]" or
        # "[2001:db8::1]:8080") contains internal colons, so only drop a
        # trailing ":port" after the closing bracket instead of splitting on
        # the last colon (which would corrupt the literal when no port is set).
        if netloc.startswith("["):
            bracket_end = netloc.find("]")
            if bracket_end != -1:
                netloc = netloc[: bracket_end + 1]
        elif ":" in netloc:
            netloc = netloc.rsplit(":", 1)[0]
        return netloc
    except (ValueError, AttributeError):
        return None


# Alias for compatibility
get_domain = extract_domain


def get_path(url: str) -> str:
    """Extract the path from a URL."""
    parsed = urlparse(url)
    return parsed.path if parsed.path else "/"


def get_query_string(url: str) -> str:
    """Extract the query string from a URL."""
    parsed = urlparse(url)
    return parsed.query


def get_fragment(url: str) -> str:
    """Extract the fragment from a URL."""
    parsed = urlparse(url)
    return parsed.fragment


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
    except (ValueError, AttributeError):
        return 0


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs are on the same domain."""
    return extract_domain(url1) == extract_domain(url2)


def is_internal_link(url: str, base_url: str) -> bool:
    """Check if URL is an internal link relative to base URL."""
    return is_same_domain(url, base_url)


def urls_are_equivalent(url1: str, url2: str) -> bool:
    """Check if two URLs are equivalent after normalization.

    Two URLs are equivalent only when both normalize to the same http/https
    URL. A URL that cannot be normalized (non-http/https scheme, or empty)
    normalizes to ``None`` and is never equivalent to anything, so two
    distinct non-normalizable URLs are not reported as equivalent.
    """
    n1 = normalize_url(url1)
    n2 = normalize_url(url2)
    if n1 is None or n2 is None:
        return False
    return n1 == n2


def remove_query_params(url: str, params: list | None = None) -> str:
    """Remove specific query parameters from URL."""
    if not params:
        return url
    try:
        parsed = urlparse(url)
        query_parts = parsed.query.split("&")
        wanted = set(params)
        filtered = [
            part for part in query_parts
            if part.split("=", 1)[0] not in wanted
        ]
        new_query = "&".join(filtered)
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
    except (ValueError, AttributeError, IndexError):
        return url


def strip_tracking_params(url: str) -> str:
    """Remove common tracking parameters from a URL."""
    tracking_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "utm_id", "fbclid", "gclid", "mc_eid", "igshid",
    }
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    cleaned = {k: v for k, v in params.items() if k not in tracking_params}
    query = urlencode(cleaned, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                       parsed.params, query, parsed.fragment))


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
    """Join a base URL with a relative URL.

    If base ends with a path (not /), relative paths are appended to it.
    If relative starts with /, it replaces the path.
    If relative is a full URL, it is returned as-is.
    """
    parsed = urlparse(relative)
    if parsed.scheme in ("http", "https"):
        return relative
    # Use urljoin but handle the case where base has a path component
    # urljoin treats base as a file if it doesn't end with /
    # We want /base + page -> /base/page
    base_parsed = urlparse(base)
    if relative.startswith("/"):
        # Absolute path replaces the entire path
        return urlunparse((
            base_parsed.scheme, base_parsed.netloc, relative,
            "", "", ""
        ))
    # Relative path: append to base path
    base_path = base_parsed.path
    if not base_path.endswith("/"):
        base_path += "/"
    new_path = base_path + relative
    return urlunparse((
        base_parsed.scheme, base_parsed.netloc, new_path,
        "", "", ""
    ))


def resolve_relative_url(base_url: str, relative_url: str) -> str | None:
    """Resolve a relative URL against a base URL."""
    parsed_base = urlparse(base_url)
    parsed_rel = urlparse(relative_url)

    # Reject javascript:, mailto:, etc.
    if parsed_rel.scheme and parsed_rel.scheme not in ("http", "https"):
        return None

    if parsed_rel.scheme:
        return relative_url

    if parsed_rel.netloc:
        return urlunparse((parsed_base.scheme, parsed_rel.netloc,
                           parsed_rel.path, parsed_rel.params,
                           parsed_rel.query, parsed_rel.fragment))

    # Relative path
    if relative_url.startswith("/"):
        path = relative_url
    else:
        base_path = parsed_base.path
        if base_path.endswith("/"):
            path = base_path + relative_url
        else:
            path = base_path.rsplit("/", 1)[0] + "/" + relative_url

    # Normalize path (resolve .. and .)
    import posixpath
    path = posixpath.normpath(path)

    return urlunparse((parsed_base.scheme, parsed_base.netloc,
                       path, parsed_rel.params,
                       parsed_rel.query, parsed_rel.fragment))


def extract_all_urls(html: str, base_url: str = "") -> list:
    """Extract all URLs from HTML content or plain text.

    If base_url is not provided, extracts URLs that are already absolute.
    Also supports extracting URLs from plain text using regex.
    """
    urls = []
    # First try to extract from HTML using BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            if href.startswith(("#", "javascript:")):
                continue
            full_url = urljoin(base_url, href) if base_url else href
            normalized = normalize_url(full_url)
            if normalized and is_valid_url(normalized):
                urls.append(normalized)
    except (ValueError, AttributeError, TypeError):
        pass

    # Also extract URLs from plain text using regex
    if not urls:
        regex_urls = re.findall(
            r'https?://[^\s<>"\')\]]+', html
        )
        for url in regex_urls:
            normalized = normalize_url(url)
            if normalized and is_valid_url(normalized) and normalized not in urls:
                urls.append(normalized)

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
    return any(path.endswith(ext) for ext in EXCLUDED_EXTENSIONS)
