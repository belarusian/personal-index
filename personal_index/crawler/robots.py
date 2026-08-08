"""Robots.txt parser for respecting crawl policies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse


@dataclass
class RobotsRule:
    """A single robots.txt rule."""

    user_agent: str
    allowed: bool
    pattern: str


class RobotsParser:
    """Parses and evaluates robots.txt rules."""

    def __init__(self) -> None:
        self._rules: list[RobotsRule] = []
        self._cache: dict[str, list[RobotsRule]] = {}

    def parse(self, content: str) -> None:
        """Parse robots.txt content.

        Args:
            content: Raw robots.txt text content.
        """
        self._rules.clear()
        current_agent = "*"

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    self._rules.append(
                        RobotsRule(user_agent=current_agent, allowed=False, pattern=path)
                    )
            elif line.lower().startswith("allow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    self._rules.append(
                        RobotsRule(user_agent=current_agent, allowed=True, pattern=path)
                    )

    def can_fetch(self, url: str, user_agent: str = "*", base_url: str = "") -> bool:
        """Check if a URL can be fetched according to robots.txt rules.

        Args:
            url: The URL to check.
            user_agent: The user agent string.
            base_url: Base URL for resolving relative paths.

        Returns:
            True if the URL can be fetched.
        """
        if not self._rules:
            return True

        parsed = urlparse(url)
        path = parsed.path or "/"

        # Find matching rules
        matching_rules = [
            r for r in self._rules
            if r.user_agent.lower() == "*" or r.user_agent.lower() == user_agent.lower()
        ]

        if not matching_rules:
            return True

        # Find the most specific matching rule
        best_match = None
        best_length = -1

        for rule in matching_rules:
            pattern = rule.pattern
            if base_url:
                pattern = urljoin(base_url, pattern)

            # Convert robots.txt pattern to regex
            regex = self._pattern_to_regex(pattern)
            if re.match(regex, path):
                if len(pattern) > best_length:
                    best_length = len(pattern)
                    best_match = rule

        if best_match is None:
            return True

        return best_match.allowed

    @staticmethod
    def _pattern_to_regex(pattern: str) -> str:
        """Convert a robots.txt pattern to a regex pattern.

        Args:
            pattern: The robots.txt pattern.

        Returns:
            A regex pattern string.
        """
        regex = re.escape(pattern)
        # Handle * wildcard
        regex = regex.replace(r"\*", ".*")
        # Handle $ anchor
        if regex.endswith(r"\$"):
            regex = regex[:-2] + "$"
        else:
            regex = regex + "$"
        return f"^{regex}"


# Alias for backward compatibility
RobotsChecker = RobotsParser
