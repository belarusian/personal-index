"""Robots.txt parser for personal-index."""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass, field
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
    rules: list[RobotsRule] = field(default_factory=list)
    crawl_delay: float = 0.0
    sitemap_urls: list[str] = field(default_factory=list)

    def can_fetch(self, url: str, user_agent: str = "personal-index") -> bool:
        """Check if a URL can be fetched according to robots.txt.

        Matching predicates applied in order:
        1. Case-insensitive user-agent match (specific rules preferred over wildcard *).
        2. Among applicable rules, the longest matching pattern wins (most specific).
        3. If no rules apply to the requested user agent, the URL is allowed (default-allow).
        """
        parsed = urlparse(url)
        path = parsed.path or "/"

        # Collect applicable rules - prefer specific user agent over wildcard
        specific_rules = []
        wildcard_rules = []
        for rule in self.rules:
            if rule.user_agent.lower() == user_agent.lower():
                specific_rules.append(rule)
            elif rule.user_agent == "*":
                wildcard_rules.append(rule)

        # Use specific rules if available, otherwise wildcard
        applicable_rules = specific_rules if specific_rules else wildcard_rules

        # If no rules apply, allow
        if not applicable_rules:
            return True

        # Check rules in order, most specific match wins
        best_match = None
        best_match_len = -1
        for rule in applicable_rules:
            pattern = rule.pattern.rstrip("/")
            if self._path_matches(path, pattern) and len(pattern) > best_match_len:
                best_match = rule
                best_match_len = len(pattern)

        if best_match is None:
            return True
        return best_match.allowed

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches a robots.txt pattern."""
        # Handle $ anchor (end of path) - exact match only
        if pattern.endswith("$"):
            pattern = pattern[:-1]
            return path == pattern

        # Handle * wildcard
        if "*" in pattern:
            regex_pattern = "^" + re.escape(pattern).replace(r"\*", ".*")
            return bool(re.match(regex_pattern, path, re.IGNORECASE))

        # Simple prefix match
        return path == pattern or path.startswith(pattern + "/")


def _parse_directive(
    line: str,
    current_agent: str | None,
    policy: RobotsPolicy,
    current_rules: list[RobotsRule],
) -> tuple[str | None, list[RobotsRule]]:
    """Parse one robots.txt line into a directive key and value.

    Splits the line on the first ":" into key and value, lowercases and
    strips the key, and dispatches on the key (user-agent, disallow, allow,
    crawl-delay, sitemap). Side effects on ``policy``: extends ``policy.rules``
    when a new user-agent is encountered, sets ``policy.crawl_delay``, and
    appends to ``policy.sitemap_urls``. Returns ``(current_agent, current_rules)``
    where ``current_agent`` is the agent string (or None) and ``current_rules``
    is the accumulated rule list for the current agent.
    """
    key, value = (line.split(":", 1) + ["", ""])[:2]
    key_lower = key.lower().strip()
    value = value.strip()

    if key_lower == "user-agent":
        if current_agent:
            policy.rules.extend(current_rules)
            current_rules = []
        current_agent = value
    elif key_lower == "disallow" and current_agent and value:
        current_rules.append(RobotsRule(current_agent, False, value))
    elif key_lower == "allow" and current_agent and value:
        current_rules.append(RobotsRule(current_agent, True, value))
    elif key_lower == "crawl-delay":
        with suppress(ValueError):
            policy.crawl_delay = float(value)
    elif key_lower == "sitemap" and value:
        policy.sitemap_urls.append(value)

    return current_agent, current_rules


def parse_robots_txt(text: str, base_url: str) -> RobotsPolicy:
    """Parse robots.txt content into a RobotsPolicy."""
    parsed = urlparse(base_url)
    domain = parsed.netloc

    policy = RobotsPolicy(domain=domain)
    current_agent = None
    current_rules: list[RobotsRule] = []

    for line in text.splitlines():
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        current_agent, current_rules = _parse_directive(
            line, current_agent, policy, current_rules
        )

    # Save last agent's rules
    if current_agent:
        policy.rules.extend(current_rules)

    return policy


def is_allowed(url: str, policy: RobotsPolicy, user_agent: str = "personal-index") -> bool:
    """Check if a URL is allowed by a robots policy."""
    return policy.can_fetch(url, user_agent)
