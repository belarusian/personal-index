"""URL deduplication with fuzzy matching and normalization."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


@dataclass
class DedupResult:
    """Result of deduplication check."""
    is_duplicate: bool
    original_url: str
    matched_url: Optional[str] = None
    similarity_score: float = 0.0
    reason: str = ""


class URLDeduplicator:
    """Deduplicate URLs using normalization and fuzzy matching."""

    def __init__(self, fuzzy_threshold: float = 0.95):
        self._seen_urls: Dict[str, str] = {}  # normalized -> original
        self._fuzzy_threshold = fuzzy_threshold
        self._url_groups: Dict[str, List[str]] = {}  # domain -> [urls]

    @property
    def seen_count(self) -> int:
        """Seen_count."""
        return len(self._seen_urls)

    def normalize_url(self, url: str) -> str:
        """Normalize a URL for comparison."""
        parsed = urlparse(url)
        normalized = parsed._replace(fragment="").geturl()

        # Remove trailing slashes (except for root)
        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            normalized = normalized.replace(path, path.rstrip("/"))

        # Normalize query parameters (sort them)
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            sorted_params = "&".join(
                f"{k}={v[0]}" for k, v in sorted(params.items())
            )
            normalized = normalized.replace(parsed.query, sorted_params)

        # Lowercase scheme and netloc
        parsed = urlparse(normalized)
        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
        ).geturl()

        # Remove www. prefix
        parsed = urlparse(normalized)
        if parsed.netloc.startswith("www."):
            normalized = parsed._replace(netloc=parsed.netloc[4:]).geturl()

        # Remove common tracking parameters
        tracking_params = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
        parsed = urlparse(normalized)
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            filtered = {k: v for k, v in params.items() if k not in tracking_params}
            if filtered:
                sorted_params = "&".join(
                    f"{k}={v[0]}" for k, v in sorted(filtered.items())
                )
                normalized = normalized.replace(parsed.query, sorted_params)
            else:
                normalized = normalized.split("?")[0]

        return normalized

    def _get_path(self, url: str) -> str:
        """Extract just the path from a URL."""
        parsed = urlparse(url)
        return parsed.path.rstrip("/") or "/"

    def check_duplicate(self, url: str) -> DedupResult:
        """Check if a URL is a duplicate of a previously seen URL."""
        normalized = self.normalize_url(url)

        # Exact match
        if normalized in self._seen_urls:
            return DedupResult(
                is_duplicate=True,
                original_url=url,
                matched_url=self._seen_urls[normalized],
                similarity_score=1.0,
                reason="exact_match",
            )

        # Fuzzy match within same domain (compare paths only)
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if domain in self._url_groups:
            path = self._get_path(normalized)
            best_match = self._find_fuzzy_match(path, self._url_groups[domain])
            if best_match:
                return DedupResult(
                    is_duplicate=True,
                    original_url=url,
                    matched_url=best_match[0],
                    similarity_score=best_match[1],
                    reason="fuzzy_match",
                )

        return DedupResult(
            is_duplicate=False,
            original_url=url,
            similarity_score=0.0,
            reason="unique",
        )

    def add_url(self, url: str) -> DedupResult:
        """Add a URL and check if it's a duplicate."""
        result = self.check_duplicate(url)

        if not result.is_duplicate:
            normalized = self.normalize_url(url)
            self._seen_urls[normalized] = url

            # Track by domain
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            if domain not in self._url_groups:
                self._url_groups[domain] = []
            self._url_groups[domain].append(url)

        return result

    def deduplicate_urls(self, urls: List[str]) -> Tuple[List[str], List[DedupResult]]:
        """Deduplicate a list of URLs, returning unique URLs and results."""
        unique_urls = []
        results = []

        for url in urls:
            result = self.add_url(url)
            results.append(result)
            if not result.is_duplicate:
                unique_urls.append(url)

        return unique_urls, results

    def _find_fuzzy_match(self, path: str, candidates: List[str]) -> Optional[Tuple[str, float]]:
        """Find the best fuzzy match among candidates (path comparison)."""
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            candidate_path = self._get_path(candidate)
            score = difflib.SequenceMatcher(None, path, candidate_path).ratio()

            if score > best_score and score >= self._fuzzy_threshold:
                best_score = score
                best_match = candidate

        if best_match:
            return (best_match, best_score)
        return None

    def get_duplicates(self) -> Dict[str, List[str]]:
        """Get all detected duplicates grouped by canonical URL."""
        duplicates: Dict[str, List[str]] = {}
        for normalized, original in self._seen_urls.items():
            parsed = urlparse(original)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            if domain in self._url_groups:
                orig_path = self._get_path(original)
                for url in self._url_groups[domain]:
                    if url != original:
                        candidate_path = self._get_path(url)
                        score = difflib.SequenceMatcher(None, orig_path, candidate_path).ratio()
                        if score >= self._fuzzy_threshold:
                            if original not in duplicates:
                                duplicates[original] = []
                            duplicates[original].append(url)
        return duplicates

    def get_stats(self) -> Dict:
        """Get deduplication statistics."""
        return {
            "total_seen": self.seen_count,
            "total_domains": len(self._url_groups),
            "total_duplicate_groups": len(self.get_duplicates()),
        }

    def clear(self):
        """Clear all seen URLs."""
        self._seen_urls.clear()
        self._url_groups.clear()

    def get_canonical_url(self, url: str) -> Optional[str]:
        """Get the canonical (first seen) URL for a given URL."""
        normalized = self.normalize_url(url)
        return self._seen_urls.get(normalized)

    def get_domain_urls(self, domain: str) -> List[str]:
        """Get all URLs for a specific domain."""
        clean_domain = domain.lower().lstrip("www.")
        return self._url_groups.get(clean_domain, [])
