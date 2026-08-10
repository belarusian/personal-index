"""Link analysis for crawled pages."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class LinkStats:
    """Statistics about links on a page."""

    total_links: int = 0
    internal_links: int = 0
    external_links: int = 0
    unique_domains: int = 0
    broken_links: int = 0
    anchor_text_distribution: dict[str, int] = field(default_factory=dict)
    domain_distribution: dict[str, int] = field(default_factory=dict)


@dataclass
class LinkAnalysisResult:
    """Result of link analysis."""

    url: str
    stats: LinkStats
    top_anchor_texts: list[tuple[str, int]] = field(default_factory=list)
    top_domains: list[tuple[str, int]] = field(default_factory=list)
    suspicious_links: list[str] = field(default_factory=list)


class LinkAnalyzer:
    """Analyzes links on crawled pages."""

    def __init__(self, base_domain: str = "", max_anchor_length: int = 100):
        self.base_domain = base_domain
        self.max_anchor_length = max_anchor_length

    def analyze(self, url: str, links: list[dict]) -> LinkAnalysisResult:
        """Analyze links found on a page."""
        stats = LinkStats()
        anchor_counter: Counter = Counter()
        domain_counter: Counter = Counter()
        suspicious = []

        for link in links:
            link_url = link.get("url", "")
            anchor = link.get("text", "").strip()

            if not link_url:
                continue

            stats.total_links += 1

            # Classify internal vs external
            parsed = urlparse(link_url)
            link_domain = parsed.netloc.lower()

            if self._is_internal(link_url):
                stats.internal_links += 1
            else:
                stats.external_links += 1
                if link_domain:
                    domain_counter[link_domain] += 1

            # Track anchor text
            if anchor:
                truncated = anchor[:self.max_anchor_length]
                anchor_counter[truncated] += 1

            # Detect suspicious links
            if self._is_suspicious(link_url, anchor):
                suspicious.append(link_url)

        stats.unique_domains = len(domain_counter)
        stats.anchor_text_distribution = dict(anchor_counter.most_common(20))
        stats.domain_distribution = dict(domain_counter.most_common(20))

        return LinkAnalysisResult(
            url=url,
            stats=stats,
            top_anchor_texts=anchor_counter.most_common(10),
            top_domains=domain_counter.most_common(10),
            suspicious_links=suspicious,
        )

    def _is_internal(self, url: str) -> bool:
        """Check if a URL is internal to the base domain."""
        if not self.base_domain:
            return False
        parsed = urlparse(url)
        return parsed.netloc.lower() == self.base_domain.lower()

    def _is_suspicious(self, url: str, anchor: str) -> bool:
        """Detect potentially suspicious links."""
        # Empty anchor text
        if not anchor.strip():
            return True
        # Generic anchor text
        generic = {"click here", "link", "here", "read more", "more", "this"}
        if anchor.lower().strip() in generic:
            return True
        # Very long URLs (possible tracking/spam)
        return len(url) > 500

    def analyze_batch(self, pages: list[dict]) -> list[LinkAnalysisResult]:
        """Analyze links across multiple pages."""
        results = []
        for page in pages:
            result = self.analyze(page.get("url", ""), page.get("links", []))
            results.append(result)
        return results

    def get_aggregate_stats(self, results: list[LinkAnalysisResult]) -> dict:
        """Get aggregate statistics across multiple analyses."""
        total_links = sum(r.stats.total_links for r in results)
        total_internal = sum(r.stats.internal_links for r in results)
        total_external = sum(r.stats.external_links for r in results)
        all_domains: set[str] = set()
        for r in results:
            all_domains.update(r.stats.domain_distribution.keys())

        return {
            "pages_analyzed": len(results),
            "total_links": total_links,
            "internal_links": total_internal,
            "external_links": total_external,
            "unique_external_domains": len(all_domains),
            "total_suspicious": sum(len(r.suspicious_links) for r in results),
        }
