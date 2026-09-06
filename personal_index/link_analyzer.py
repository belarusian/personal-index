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
        """Analyze links found on a page.

        Skips any link whose ``url`` is empty. For each remaining link
        it increments ``stats.total_links`` and classifies it as
        internal (``stats.internal_links``) or external
        (``stats.external_links``); external links also feed the domain
        counter. Anchor text is stripped and truncated to
        ``max_anchor_length`` before counting. Links flagged by
        ``_is_suspicious`` are appended to the suspicious list.

        Sets ``stats.unique_domains`` to the number of distinct external
        domains and stores the top-20 anchor and domain distributions on
        ``stats``. Returns a ``LinkAnalysisResult`` whose
        ``top_anchor_texts`` and ``top_domains`` are the top-10 entries
        and ``suspicious_links`` is the flagged list.
        """
        stats = LinkStats()
        anchor_counter: Counter = Counter()
        domain_counter: Counter = Counter()
        suspicious: list[str] = []

        for link in links:
            link_url = link.get("url", "")
            if not link_url:
                continue
            self._analyze_single_link(link_url, link.get("text", ""), stats, anchor_counter, domain_counter, suspicious)

        stats.unique_domains = len(domain_counter)
        stats.anchor_text_distribution = dict(anchor_counter.most_common(20))
        stats.domain_distribution = dict(domain_counter.most_common(20))

        return LinkAnalysisResult(
            url=url, stats=stats,
            top_anchor_texts=anchor_counter.most_common(10),
            top_domains=domain_counter.most_common(10),
            suspicious_links=suspicious,
        )

    def _analyze_single_link(
        self, link_url: str, anchor: str, stats: LinkStats,
        anchor_counter: Counter, domain_counter: Counter, suspicious: list[str],
    ) -> None:
        """Process a single link, updating stats and counters."""
        stats.total_links += 1
        parsed = urlparse(link_url)
        link_domain = parsed.netloc.lower()

        if self._is_internal(link_url):
            stats.internal_links += 1
        else:
            stats.external_links += 1
            if link_domain:
                domain_counter[link_domain] += 1

        a = anchor.strip()
        if a:
            anchor_counter[a[:self.max_anchor_length]] += 1

        if self._is_suspicious(link_url, a):
            suspicious.append(link_url)

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
