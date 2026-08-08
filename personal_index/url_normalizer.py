"""URL normalization and canonicalization utilities."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def normalize_url(url: str, remove_fragment: bool = True,
                  lowercase_path: bool = True,
                  remove_default_port: bool = True,
                  sort_query_params: bool = True) -> str:
    """Normalize a URL by applying standard transformations."""
    parsed = urlparse(url)

    # Lowercase scheme and netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove default ports
    if remove_default_port:
        netloc = _remove_default_port(netloc, scheme)

    # Lowercase path if requested
    path = parsed.path.lower() if lowercase_path else parsed.path
    # Normalize path: remove trailing slash (except root), collapse slashes
    path = re.sub(r"/+", "/", path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Sort query parameters
    query = parsed.query
    if sort_query_params and query:
        params = parse_qs(query, keep_blank_values=True)
        query = urlencode(params, doseq=True)

    # Remove fragment
    fragment = "" if remove_fragment else parsed.fragment

    return urlunparse((scheme, netloc, path, "", query, fragment))


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


def get_domain(url: str) -> str:
    """Extract the domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def get_path(url: str) -> str:
    """Extract the path from a URL."""
    parsed = urlparse(url)
    return parsed.path


def get_query_string(url: str) -> str:
    """Extract the query string from a URL."""
    parsed = urlparse(url)
    return parsed.query


def get_fragment(url: str) -> str:
    """Extract the fragment from a URL."""
    parsed = urlparse(url)
    return parsed.fragment


def urls_are_equivalent(url1: str, url2: str) -> bool:
    """Check if two URLs are equivalent after normalization."""
    return normalize_url(url1) == normalize_url(url2)


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


def resolve_relative_url(base_url: str, relative_url: str) -> str:
    """Resolve a relative URL against a base URL."""
    parsed_base = urlparse(base_url)
    parsed_rel = urlparse(relative_url)

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

    return urlunparse((parsed_base.scheme, parsed_base.netloc,
                       path, parsed_rel.params,
                       parsed_rel.query, parsed_rel.fragment))
