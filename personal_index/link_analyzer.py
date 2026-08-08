"""Link analysis for crawled pages."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin


@dataclass
class LinkInfo:
    """Information about a single link."""
    url: str
    text: str = ""
    is_internal: bool = False
    is_external: bool = False
    is_anchor: bool = False
    is_mailto: bool = False
    is_tel: bool = False
    domain: str = ""
    path: str = ""

    def __post_init__(self):
        if not self.domain and not self.is_anchor and not self.is_mailto and not self.is_tel:
            parsed = urlparse(self.url)
            self.domain = parsed.netloc
            self.path = parsed.path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "text": self.text,
            "is_internal": self.is_internal,
            "is_external": self.is_external,
            "is_anchor": self.is_anchor,
            "is_mailto": self.is_mailto,
            "is_tel": self.is_tel,
            "domain": self.domain,
            "path": self.path,
        }


@dataclass
class LinkAnalysisResult:
    """Results of link analysis."""
    total_links: int = 0
    internal_links: int = 0
    external_links: int = 0
    anchor_links: int = 0
    mailto_links: int = 0
    unique_domains: int = 0
    domain_counts: Dict[str, int] = field(default_factory=dict)
    top_anchor_texts: List[Tuple[str, int]] = field(default_factory=list)
    broken_patterns: List[str] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_links": self.total_links,
            "internal_links": self.internal_links,
            "external_links": self.external_links,
            "anchor_links": self.anchor_links,
            "mailto_links": self.mailto_links,
            "unique_domains": self.unique_domains,
            "domain_counts": self.domain_counts,
            "top_anchor_texts": self.top_anchor_texts,
            "broken_patterns": self.broken_patterns,
        }


class LinkAnalyzer:
    """Analyze links in HTML content."""

    # Patterns for extracting links from HTML
    LINK_PATTERN = re.compile(
        r'<a\s+[^>]*href\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    SIMPLE_LINK_PATTERN = re.compile(
        r'<a\s+[^>]*href\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )

    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self._base_domain = urlparse(base_url).netloc if base_url else ""

    def analyze(self, html: str) -> LinkAnalysisResult:
        """Analyze all links in HTML content."""
        links = self._extract_links(html)
        result = LinkAnalysisResult(total_links=len(links))

        domains: Set[str] = set()
        domain_counter: Counter = Counter()
        anchor_texts: Counter = Counter()

        for link in links:
            if link.is_internal:
                result.internal_links += 1
            elif link.is_external:
                result.external_links += 1
                if link.domain:
                    domains.add(link.domain)
                    domain_counter[link.domain] += 1
            elif link.is_anchor:
                result.anchor_links += 1
            elif link.is_mailto:
                result.mailto_links += 1

            if link.text.strip():
                anchor_texts[link.text.strip()] += 1

            result.links.append(link.to_dict())

        result.unique_domains = len(domains)
        result.domain_counts = dict(domain_counter.most_common(20))
        result.top_anchor_texts = anchor_texts.most_common(10)
        result.broken_patterns = self._detect_broken_patterns(links)

        return result

    def extract_links(self, html: str) -> List[str]:
        """Extract all URLs from HTML."""
        links = self._extract_links(html)
        return [l.url for l in links]

    def get_external_links(self, html: str) -> List[str]:
        """Extract only external links."""
        links = self._extract_links(html)
        return [l.url for l in links if l.is_external]

    def get_internal_links(self, html: str) -> List[str]:
        """Extract only internal links."""
        links = self._extract_links(html)
        return [l.url for l in links if l.is_internal]

    def get_link_text_pairs(self, html: str) -> List[Tuple[str, str]]:
        """Get (url, text) pairs from HTML."""
        links = self._extract_links(html)
        return [(l.url, l.text.strip()) for l in links if l.text.strip()]

    def _extract_links(self, html: str) -> List[LinkInfo]:
        """Extract and classify links from HTML."""
        links = []
        seen = set()

        # Try full pattern first
        matches = self.LINK_PATTERN.findall(html)
        if not matches:
            matches = [(m, "") for m in self.SIMPLE_LINK_PATTERN.findall(html)]

        for url, text in matches:
            url = url.strip()
            if not url or url in seen:
                continue
            seen.add(url)

            # Clean text
            text = re.sub(r'<[^>]+>', '', text).strip()
            text = re.sub(r'\s+', ' ', text).strip()

            # Resolve relative URLs
            if self.base_url and not url.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', 'javascript:')):
                url = urljoin(self.base_url, url)

            link = LinkInfo(url=url, text=text)

            # Classify
            if url.startswith('#'):
                link.is_anchor = True
            elif url.startswith('mailto:'):
                link.is_mailto = True
            elif url.startswith('tel:'):
                link.is_tel = True
            elif self._base_domain and link.domain == self._base_domain:
                link.is_internal = True
            elif link.domain and not url.startswith('javascript:'):
                link.is_external = True

            links.append(link)

        return links

    def _detect_broken_patterns(self, links: List[LinkInfo]) -> List[str]:
        """Detect potentially broken link patterns."""
        patterns = []
        for link in links:
            if link.url.startswith('//') and not link.url.startswith('http'):
                patterns.append(f"Protocol-relative URL: {link.url}")
            elif link.url == '#':
                patterns.append(f"Empty anchor: {link.url}")
            elif 'javascript:void' in link.url.lower():
                patterns.append(f"JavaScript void link: {link.url}")
            elif link.url.startswith('file://'):
                patterns.append(f"File protocol link: {link.url}")
        return patterns
