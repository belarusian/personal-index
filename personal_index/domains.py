"""Domain management for crawling rules."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class DomainRule:
    """Rule for a specific domain."""

    domain: str
    allowed: bool = True
    max_pages: int = 100
    max_depth: int = 3
    reason: str = ""

    def to_dict(self) -> dict:
        """Serialize the domain rule to a dictionary.

        Returns:
            Dictionary representation of the rule.
        """
        return {
            "domain": self.domain,
            "allowed": self.allowed,
            "max_pages": self.max_pages,
            "max_depth": self.max_depth,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DomainRule:
        """Create a DomainRule from a dictionary.

        Args:
            data: Dictionary with rule fields.

        Returns:
            A new DomainRule instance.
        """
        return cls(**data)


@dataclass
class DomainManager:
    """Manages domain allow/block rules."""

    rules_file: str | None = None
    _rules: dict[str, DomainRule] = field(default_factory=dict, repr=False)
    _page_counts: dict[str, int] = field(default_factory=dict, repr=False)
    _has_whitelist: bool = False

    def __post_init__(self):
        if self.rules_file and os.path.exists(self.rules_file):
            self._load()

    def _load(self) -> None:
        if not self.rules_file:
            return
        try:
            with open(self.rules_file, "r") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                self._rules = {}
                return
            self._rules = {
                d: DomainRule.from_dict(r) for d, r in data.items()
            }
            self._has_whitelist = any(
                r.allowed for r in self._rules.values()
            )
        except (json.JSONDecodeError, KeyError):
            self._rules = {}

    def _save(self) -> None:
        if not self.rules_file:
            return
        os.makedirs(
            os.path.dirname(self.rules_file) or ".", exist_ok=True
        )
        data = {d: r.to_dict() for d, r in self._rules.items()}
        with open(self.rules_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_allow(
        self, domain: str, max_pages: int = 100, max_depth: int = 3
    ) -> None:
        """Add an allow rule for a domain.

        Args:
            domain: The domain to allow.
            max_pages: Maximum pages to crawl from this domain.
            max_depth: Maximum crawl depth for this domain.
        """
        self._rules[domain] = DomainRule(
            domain=domain, allowed=True,
            max_pages=max_pages, max_depth=max_depth
        )
        self._has_whitelist = True
        self._save()

    def add_block(self, domain: str, reason: str = "") -> None:
        """Add a block rule for a domain.

        Args:
            domain: The domain to block.
            reason: Optional reason for blocking.
        """
        self._rules[domain] = DomainRule(
            domain=domain, allowed=False, reason=reason
        )
        self._save()

    def is_allowed(self, domain: str) -> bool:
        """Check if a domain is allowed for crawling.

        Args:
            domain: The domain to check.

        Returns:
            True if the domain is allowed, False otherwise.
        """
        if domain in self._rules:
            rule = self._rules[domain]
            if not rule.allowed:
                return False
            return not self._page_counts.get(domain, 0) >= rule.max_pages
        return not self._has_whitelist

    def is_blocked(self, domain: str) -> bool:
        """Check if a domain is explicitly blocked.

        Args:
            domain: The domain to check.

        Returns:
            True if the domain is blocked, False otherwise.
        """
        if domain in self._rules:
            return not self._rules[domain].allowed
        return False

    def record_page(self, domain: str) -> None:
        """Record that a page was crawled from a domain."""
        self._page_counts[domain] = self._page_counts.get(domain, 0) + 1

    def get_page_count(self, domain: str) -> int:
        """Get the number of pages crawled from a domain.

        Args:
            domain: The domain to check.

        Returns:
            Number of pages crawled.
        """
        return self._page_counts.get(domain, 0)

    def reset_counts(self) -> None:
        """Reset all page counts."""
        self._page_counts = {}

    def remove(self, domain: str) -> bool:
        """Remove a domain rule.

        Args:
            domain: The domain whose rule to remove.

        Returns:
            True if a rule was removed, False if not found.
        """
        if domain in self._rules:
            del self._rules[domain]
            self._save()
            return True
        return False

    def list_rules(self) -> list[DomainRule]:
        """List all domain rules.

        Returns:
            List of all DomainRule objects.
        """
        return list(self._rules.values())

    def get_max_depth(self, domain: str) -> int:
        """Get the maximum crawl depth for a domain.

        Args:
            domain: The domain to check.

        Returns:
            Maximum depth (defaults to 3 if no rule exists).
        """
        if domain in self._rules:
            return self._rules[domain].max_depth
        return 3
