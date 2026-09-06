"""URL filtering with blacklist and whitelist support."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass


@dataclass
class UrlFilterRule:
    """A single URL filter rule."""
    pattern: str
    is_blacklist: bool = True
    description: str = ""

    def matches(self, url: str) -> bool:
        """Check if URL matches this rule's pattern."""
        # Support exact match
        if self.pattern == url:
            return True
        # Support fnmatch-style wildcards
        if fnmatch.fnmatch(url, self.pattern):
            return True
        # Support regex patterns (prefixed with re:)
        if self.pattern.startswith("re:"):
            regex = self.pattern[3:]
            try:
                return bool(re.search(regex, url))
            except re.error:
                return False
        return False


class UrlFilter:
    """Filter URLs based on blacklist and whitelist rules.

    Whitelist rules take precedence over blacklist rules.
    If a URL matches any whitelist rule, it passes.
    If no whitelist match, check against blacklist.
    """

    def __init__(self):
        self._blacklist: list[UrlFilterRule] = []
        self._whitelist: list[UrlFilterRule] = []

    def add_blacklist(self, pattern: str, description: str = "") -> None:
        """Add a URL pattern to the blacklist."""
        self._blacklist.append(UrlFilterRule(pattern, is_blacklist=True, description=description))

    def add_whitelist(self, pattern: str, description: str = "") -> None:
        """Add a URL pattern to the whitelist."""
        self._whitelist.append(UrlFilterRule(pattern, is_blacklist=False, description=description))

    def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed (passes all filters).

        Args:
            url: URL to check.

        Returns:
            True if URL is allowed, False if blocked.
        """
        # Check whitelist first (takes precedence)
        for rule in self._whitelist:
            if rule.matches(url):
                return True
        # Check blacklist
        return all(not rule.matches(url) for rule in self._blacklist)

    def is_blocked(self, url: str) -> bool:
        """Check if a URL is blocked.

        Args:
            url: URL to check.

        Returns:
            True if URL is blocked, False if allowed.
        """
        return not self.is_allowed(url)

    def filter_urls(self, urls: list[str]) -> list[str]:
        """Filter a list of URLs, returning only allowed ones.

        Args:
            urls: List of URLs to filter.

        Returns:
            List of allowed URLs.
        """
        return [url for url in urls if self.is_allowed(url)]

    def get_blocked_urls(self, urls: list[str]) -> list[str]:
        """Return URLs that are blocked.

        Args:
            urls: List of URLs to check.

        Returns:
            List of blocked URLs.
        """
        return [url for url in urls if self.is_blocked(url)]

    def get_matching_rule(self, url: str) -> UrlFilterRule | None:
        """Return the first rule matching ``url``, or ``None`` if none matches.

        The WHITELIST is scanned first (whitelist takes precedence over
        blacklist); only when no whitelist rule matches is the BLACKLIST
        scanned. Within each list, rules are checked in insertion order and
        the FIRST rule whose ``matches(url)`` is True is returned.

        Args:
            url: URL to check.

        Returns:
            The actual stored ``UrlFilterRule`` object (identity, not a copy)
            for the first matching rule, or ``None`` when neither list has a
            matching rule (including an empty filter). Pure accessor: does not
            mutate ``_whitelist`` or ``_blacklist``.
        """
        for rule in self._whitelist:
            if rule.matches(url):
                return rule
        for rule in self._blacklist:
            if rule.matches(url):
                return rule
        return None

    @property
    def blacklist_count(self) -> int:
        """Number of blacklist rules."""
        return len(self._blacklist)

    @property
    def whitelist_count(self) -> int:
        """Number of whitelist rules."""
        return len(self._whitelist)

    def clear(self) -> None:
        """Clear all rules."""
        self._blacklist.clear()
        self._whitelist.clear()

    def clear_blacklist(self) -> None:
        """Clear all blacklist rules."""
        self._blacklist.clear()

    def clear_whitelist(self) -> None:
        """Clear all whitelist rules."""
        self._whitelist.clear()
