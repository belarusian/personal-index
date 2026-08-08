"""Robots.txt parser for personal-index.

Parses and enforces robots.txt rules for polite crawling.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


@dataclass
class RobotsRule:
    """A single robots.txt rule."""

    user_agent: str
    allowed: bool
    path_pattern: str

    def matches_path(self, path: str) -> bool:
        """Check if a path matches this rule."""
        # Convert robots.txt wildcards to regex
        pattern = self.path_pattern.replace("*", ".*").replace("?", ".")
        pattern = f"^{pattern}$"
        try:
            return bool(re.match(pattern, path, re.IGNORECASE))
        except re.error:
            return False


class RobotsParser:
    """Parses and evaluates robots.txt rules."""

    def __init__(self):
        self._cache: dict[str, list[RobotsRule]] = {}
        self._session = requests.Session()

    def fetch_robots_txt(self, url: str, timeout: int = 10) -> str | None:
        """Fetch robots.txt from a URL's domain.

        Args:
            url: Any URL on the domain.
            timeout: Request timeout in seconds.

        Returns:
            robots.txt content or None if not found.
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            response = self._session.get(
                robots_url,
                timeout=timeout,
                headers={"User-Agent": "personal-index/0.1.0"},
            )
            if response.status_code == 200:
                return response.text
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch robots.txt from {robots_url}: {e}")

        return None

    def parse(self, robots_txt: str) -> list[RobotsRule]:
        """Parse robots.txt content into rules.

        Args:
            robots_txt: Raw robots.txt content.

        Returns:
            List of RobotsRule objects.
        """
        rules = []
        current_agent = "*"
        lines = robots_txt.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.lower().startswith("allow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    rules.append(RobotsRule(
                        user_agent=current_agent,
                        allowed=True,
                        path_pattern=path,
                    ))
            elif line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    rules.append(RobotsRule(
                        user_agent=current_agent,
                        allowed=False,
                        path_pattern=path,
                    ))
                else:
                    # Empty disallow means everything is allowed
                    rules.append(RobotsRule(
                        user_agent=current_agent,
                        allowed=True,
                        path_pattern="*",
                    ))
            elif line.lower().startswith("sitemap:"):
                pass  # Sitemaps are handled separately

        return rules

    def is_allowed(self, url: str, user_agent: str = "personal-index") -> bool:
        """Check if a URL is allowed by robots.txt.

        Args:
            url: URL to check.
            user_agent: User agent string to match against.

        Returns:
            True if the URL is allowed, False otherwise.
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path or "/"

        # Check cache
        if domain not in self._cache:
            robots_txt = self.fetch_robots_txt(url)
            if robots_txt:
                self._cache[domain] = self.parse(robots_txt)
            else:
                # No robots.txt means everything is allowed
                self._cache[domain] = []

        rules = self._cache[domain]
        if not rules:
            return True

        # Find matching rules for this user agent
        matching_rules = [
            r for r in rules
            if r.user_agent == "*" or r.user_agent.lower() == user_agent.lower()
        ]

        if not matching_rules:
            return True

        # Find the most specific matching rule
        best_match = None
        best_length = -1

        for rule in matching_rules:
            if rule.matches_path(path):
                if len(rule.path_pattern) > best_length:
                    best_match = rule
                    best_length = len(rule.path_pattern)

        if best_match is None:
            return True

        return best_match.allowed

    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
