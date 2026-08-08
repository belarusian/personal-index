"""Robots.txt parser."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse


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
    rules: List[RobotsRule] = field(default_factory=list)
    crawl_delay: float = 0.0
    sitemap_urls: List[str] = field(default_factory=list)

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if a URL can be fetched."""
        parsed = urlparse(url)
        path = parsed.path or "/"

        # Find applicable rules
        applicable_rules = []
        for rule in self.rules:
            if rule.user_agent == "*" or rule.user_agent.lower() == user_agent.lower():
                applicable_rules.append(rule)

        if not applicable_rules:
            return True

        # Find the most specific matching rule
        best_match = None
        best_length = -1
        for rule in applicable_rules:
            pattern = rule.pattern.rstrip("/")
            if self._matches(path, pattern):
                if len(pattern) > best_length:
                    best_length = len(pattern)
                    best_match = rule

        if best_match is None:
            return True
        return best_match.allowed

    @staticmethod
    def _matches(path: str, pattern: str) -> bool:
        """Check if path matches a robots.txt pattern."""
        if pattern == "*":
            return True
        # Handle $ anchor
        if pattern.endswith("$"):
            pattern = pattern[:-1]
            return fnmatch.fnmatch(path, pattern) or path == pattern
        # Handle wildcard
        if "*" in pattern:
            return fnmatch.fnmatch(path, pattern)
        # Prefix match
        return path.startswith(pattern)


def parse_robots_txt(text: str, base_url: str = "") -> RobotsPolicy:
    """Parse robots.txt content into a RobotsPolicy."""
    parsed = urlparse(base_url)
    domain = parsed.netloc or ""
    policy = RobotsPolicy(domain=domain)

    current_agent = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            current_agent = value
        elif key == "disallow" and current_agent:
            policy.rules.append(RobotsRule(user_agent=current_agent, allowed=False, pattern=value))
        elif key == "allow" and current_agent:
            policy.rules.append(RobotsRule(user_agent=current_agent, allowed=True, pattern=value))
        elif key == "crawl-delay":
            try:
                policy.crawl_delay = float(value)
            except ValueError:
                pass
        elif key == "sitemap":
            policy.sitemap_urls.append(value)

    return policy


def is_allowed(url: str, policy: RobotsPolicy) -> bool:
    """Check if URL is allowed by robots policy."""
    return policy.can_fetch(url)


class RobotsParser:
    """Simple robots.txt parser."""

    def __init__(self):
        self._rules: List[RobotsRule] = []
        self._policies: Dict[str, RobotsPolicy] = {}

    def parse(self, text: str, base_url: str = "") -> None:
        """Parse robots.txt text."""
        policy = parse_robots_txt(text, base_url)
        self._rules = policy.rules

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain in self._policies:
            return self._policies[domain].can_fetch(url, user_agent)
        # Use inline rules
        path = parsed.path or "/"
        applicable = [r for r in self._rules if r.user_agent == "*" or r.user_agent.lower() == user_agent.lower()]
        if not applicable:
            return True
        best_match = None
        best_len = -1
        for rule in applicable:
            pattern = rule.pattern.rstrip("/")
            if RobotsPolicy._matches(path, pattern):
                if len(pattern) > best_len:
                    best_len = len(pattern)
                    best_match = rule
        if best_match is None:
            return True
        return best_match.allowed
