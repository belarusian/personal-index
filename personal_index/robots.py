"""Robots.txt parser for personal-index.

Handles parsing and caching of robots.txt files to respect
crawler access rules.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from typing import Optional
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
        """Check if this rule matches the given path."""
        if not self.path_pattern:
            return False

        if self.path_pattern == "*":
            return True

        # Exact match
        if self.path_pattern == path:
            return True

        # Wildcard match using fnmatch
        if fnmatch.fnmatch(path, self.path_pattern):
            return True

        return False


class RobotsParser:
    """Parses and caches robots.txt files."""

    def __init__(self):
        self._cache: dict[str, list[RobotsRule]] = {}
        self._session = requests.Session()

    def parse(self, content: str) -> list[RobotsRule]:
        """Parse robots.txt content into rules.

        Args:
            content: Raw robots.txt content.

        Returns:
            List of RobotsRule objects.
        """
        rules: list[RobotsRule] = []
        current_agent = "*"

        for line in content.splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if not path:
                    # Empty Disallow means allow all
                    rules.append(RobotsRule(
                        user_agent=current_agent,
                        allowed=True,
                        path_pattern="*",
                    ))
                else:
                    rules.append(RobotsRule(
                        user_agent=current_agent,
                        allowed=False,
                        path_pattern=path,
                    ))
            elif line.lower().startswith("allow:"):
                path = line.split(":", 1)[1].strip()
                rules.append(RobotsRule(
                    user_agent=current_agent,
                    allowed=True,
                    path_pattern=path,
                ))

        return rules

    def fetch_robots_txt(self, url: str) -> Optional[str]:
        """Fetch robots.txt for the domain of the given URL.

        Args:
            url: Any URL on the target domain.

        Returns:
            robots.txt content or None if not found.
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            response = self._session.get(robots_url, timeout=5)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.debug(f"Failed to fetch robots.txt from {robots_url}: {e}")

        return None

    def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed by robots.txt rules.

        Args:
            url: URL to check.

        Returns:
            True if the URL is allowed to be crawled.
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path or "/"

        # Get or fetch rules for this domain
        if domain not in self._cache:
            content = self.fetch_robots_txt(url)
            if content:
                self._cache[domain] = self.parse(content)
            else:
                self._cache[domain] = []

        rules = self._cache[domain]

        # No rules means everything is allowed
        if not rules:
            return True

        # Find matching rules (most specific wins)
        matching_rules = [r for r in rules if r.matches_path(path)]

        if not matching_rules:
            return True

        # Most specific (longest pattern) rule wins
        best_rule = max(matching_rules, key=lambda r: len(r.path_pattern))
        return best_rule.allowed

    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
