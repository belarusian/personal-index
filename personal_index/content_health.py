"""Content health monitoring for personal index.

Provides a lightweight health check for the content subsystem,
returning status, timestamp, and a numeric score.

Also provides URL accessibility checking for saved content URLs.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests


# ---------------------------------------------------------------------------
# Original filesystem health check (unchanged)
# ---------------------------------------------------------------------------


def check_health(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Check overall content health status.

    Args:
        data_dir: Path to data directory.

    Returns:
        Dict with health status, score, and details.
    """
    """Run a health check on the content subsystem.

    Args:
        data_dir: Optional path to the data directory. Defaults to
            ~/.personal_index if not provided.

    Returns:
        A dict with keys:
            - status: "healthy", "degraded", or "unhealthy"
            - last_check: ISO 8601 timestamp of when the check ran
            - score: numeric score from 0.0 to 1.0
    """
    if data_dir is None:
        data_dir = str(Path.home() / ".personal_index")

    score = 1.0
    issues: list[str] = []

    # Check 1: data directory exists
    data_path = Path(data_dir)
    if not data_path.exists():
        score -= 0.3
        issues.append("data directory missing")
    elif not data_path.is_dir():
        score -= 0.3
        issues.append("data path is not a directory")

    # Check 2: data directory is readable
    if data_path.exists() and not os.access(str(data_path), os.R_OK):
        score -= 0.2
        issues.append("data directory not readable")

    # Check 3: data directory is writable
    if data_path.exists() and not os.access(str(data_path), os.W_OK):
        score -= 0.2
        issues.append("data directory not writable")

    # Check 4: storage database exists
    storage_path = data_path / "storage.db"
    if data_path.exists() and not storage_path.exists():
        score -= 0.15
        issues.append("storage database missing")

    # Check 5: config file exists
    config_path = data_path / "config.yaml"
    if data_path.exists() and not config_path.exists():
        score -= 0.1
        issues.append("config file missing")

    # Clamp score to [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    # Determine status from score
    if score >= 0.8:
        status = "healthy"
    elif score >= 0.5:
        status = "degraded"
    else:
        status = "unhealthy"

    last_check = datetime.now(timezone.utc).isoformat()

    return {
        "status": status,
        "last_check": last_check,
        "score": score,
    }


# ---------------------------------------------------------------------------
# URL accessibility health check (new)
# ---------------------------------------------------------------------------


@dataclass
class UrlHealthResult:
    """Result of URL health check.

    Attributes:
        url: The checked URL.
        status: HTTP status code.
        accessible: Whether URL is reachable.
    """
    """Result of checking a single URL's accessibility."""

    url: str
    status_code: Optional[int]
    is_accessible: bool
    error: Optional[str]
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "url": self.url,
            "status_code": self.status_code,
            "is_accessible": self.is_accessible,
            "error": self.error,
            "checked_at": self.checked_at,
        }


def _is_valid_http_url(url: str) -> bool:
    """Validate if URL is a proper HTTP/HTTPS URL.

    Args:
        url: URL string to validate.

    Returns:
        True if valid HTTP URL.
    """
    """Check if a URL looks like a valid HTTP(S) URL."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def check_url_accessibility(
    url: str,
    timeout: int = 5,
) -> UrlHealthResult:
    """Check if a URL is accessible.

    Args:
        url: URL to check.
        timeout: Request timeout in seconds.

    Returns:
        UrlHealthResult with status info.
    """
    """Check whether a single URL is still accessible.

    Uses HEAD first, falling back to GET if the server returns 405.

    Args:
        url: The URL to check.
        timeout: Request timeout in seconds.

    Returns:
        A UrlHealthResult describing the outcome.
    """
    if not _is_valid_http_url(url):
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error="Invalid URL",
        )

    try:
        # Try HEAD first (lighter weight)
        resp = requests.head(url, timeout=timeout, allow_redirects=True)

        # If server doesn't support HEAD, fall back to GET
        if resp.status_code == 405:
            resp = requests.get(url, timeout=timeout, allow_redirects=True)

        is_accessible = resp.status_code < 400
        error = None if is_accessible else f"HTTP {resp.status_code}"

        return UrlHealthResult(
            url=url,
            status_code=resp.status_code,
            is_accessible=is_accessible,
            error=error,
        )

    except requests.Timeout:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error="Request timed out",
        )
    except requests.ConnectionError as exc:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error=f"Connection error: {exc}",
        )
    except requests.RequestException as exc:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error=f"Request failed: {exc}",
        )
    except Exception as exc:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error=f"Unexpected error: {exc}",
        )


def check_content_urls(
    storage: Any,
    timeout: int = 5,
) -> List[UrlHealthResult]:
    """Check accessibility of multiple content URLs.

    Args:
        urls: List of URLs to check.
        timeout: Request timeout.

    Returns:
        List of UrlHealthResult objects.
    """
    """Check accessibility of all saved content URLs.

    Iterates over every IndexedPage in the storage and checks whether
    its URL is still reachable.

    Args:
        storage: A storage object with a ``get_pages()`` method that
            returns a list of IndexedPage instances.
        timeout: Request timeout in seconds per URL.

    Returns:
        A list of UrlHealthResult, one per saved URL.
    """
    pages = storage.get_pages()
    results: List[UrlHealthResult] = []
    for page in pages:
        result = check_url_accessibility(page.url, timeout=timeout)
        results.append(result)
    return results
