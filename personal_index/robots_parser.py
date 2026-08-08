"""Robots.txt parser for respecting crawl policies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


@dataclass
class RobotsRule:
    """A single robots.txt rule."""

    user_agent: str
    allowed: bool
    pattern: str


@dataclass
class RobotsPolicy:
    """Parsed robots.txt policy for a domain."""

    domain: str
    rules: list[RobotsRule] = None
    crawl_delay: float = 0.0
    sitemap_urls: list[str] = None

    def __post_init__(self):
        if self.rules is None:
            self.rules = []
        if self.sitemap_urls is None:
            self.sitemap_urls = []

    def can_fetch(self, url: str, user_agent: str = "personal-index") -> bool:
        """Check if a URL can be fetched according to robots.txt."""
        path = urlparse(url).path
        if not path:
            path = "/"

        matching_rules = []
        for rule in self.rules:
            if rule.user_agent == "*" or rule.user_agent.lower() == user_agent.lower():
                matching_rules.append(rule)

        if not matching_rules:
            return True

        # Find the most specific matching rule
        best_match = None
        best_specificity = -1

        for rule in matching_rules:
            pattern = rule.pattern.rstrip("*")
            if self._url_matches_pattern(path, rule.pattern):
                specificity = len(pattern)
                if specificity > best_specificity:
                    best_specificity = specificity
                    best_match = rule

        if best_match is None:
            return True

        return best_match.allowed

    @staticmethod
    def _url_matches_pattern(path: str, pattern: str) -> bool:
        """Check if a URL path matches a robots.txt pattern."""
        if pattern == "*":
            return True

        # Convert robots.txt pattern to regex
        regex_pattern = "^"
        for char in pattern:
            if char == "*":
                regex_pattern += ".*"
            elif char == "$":
                regex_pattern += "$"
            else:
                regex_pattern += re.escape(char)

        return bool(re.match(regex_pattern, path))


def parse_robots_txt(text: str, base_url: str = "") -> RobotsPolicy:
    """Parse robots.txt content into a RobotsPolicy."""
    domain = urlparse(base_url).netloc if base_url else ""
    policy = RobotsPolicy(domain=domain)
    rules = []
    current_user_agent = None

    for line in text.splitlines():
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        # Remove inline comments
        if "#" in line:
            line = line[:line.index("#")].strip()

        if line.lower().startswith("user-agent:"):
            current_user_agent = line.split(":", 1)[1].strip()
        elif line.lower().startswith("disallow:"):
            pattern = line.split(":", 1)[1].strip()
            if current_user_agent and pattern:
                rules.append(RobotsRule(
                    user_agent=current_user_agent,
                    allowed=False,
                    pattern=pattern,
                ))
        elif line.lower().startswith("allow:"):
            pattern = line.split(":", 1)[1].strip()
            if current_user_agent and pattern:
                rules.append(RobotsRule(
                    user_agent=current_user_agent,
                    allowed=True,
                    pattern=pattern,
                ))
        elif line.lower().startswith("crawl-delay:"):
            try:
                policy.crawl_delay = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            if sitemap_url:
                policy.sitemap_urls.append(urljoin(base_url, sitemap_url))

    policy.rules = rules
    return policy


def is_allowed(url: str, policy: RobotsPolicy, user_agent: str = "personal-index") -> bool:
    """Check if a URL is allowed by the robots policy."""
    return policy.can_fetch(url, user_agent)
