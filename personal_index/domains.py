"""
Domain management for personal-index.

Manages domain allowlists and blocklists for the crawler.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DomainRule:
    """A rule for a specific domain."""
    domain: str
    allowed: bool = True
    max_pages: int = 100
    max_depth: int = 3
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "allowed": self.allowed,
            "max_pages": self.max_pages,
            "max_depth": self.max_depth,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DomainRule":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class DomainManager:
    """Manages domain allowlists and blocklists."""

    def __init__(self, rules_file: Optional[str] = None):
        self._rules_file = rules_file
        self._rules: dict[str, DomainRule] = {}
        self._page_counts: dict[str, int] = {}
        self._load()

    def _get_default_path(self) -> str:
        config_dir = Path.home() / ".config" / "personal-index"
        return str(config_dir / "domains.json")

    def _load(self) -> None:
        """Load domain rules from file."""
        path = Path(self._rules_file or self._get_default_path())
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                for domain, rule_data in data.items():
                    self._rules[domain] = DomainRule.from_dict(rule_data)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self) -> None:
        """Save domain rules to file."""
        path = Path(self._rules_file or self._get_default_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({d: r.to_dict() for d, r in self._rules.items()}, f, indent=2)

    def is_allowed(self, domain: str) -> bool:
        """Check if a domain is allowed for crawling."""
        if domain in self._rules:
            rule = self._rules[domain]
            if not rule.allowed:
                return False
            if self._page_counts.get(domain, 0) >= rule.max_pages:
                return False
            return True

        # If no explicit rule, check if we have a whitelist
        if self._has_whitelist():
            return False
        return True

    def _has_whitelist(self) -> bool:
        """Check if we have any allowlisted domains."""
        return any(r.allowed for r in self._rules.values())

    def is_blocked(self, domain: str) -> bool:
        """Check if a domain is explicitly blocked."""
        if domain in self._rules:
            return not self._rules[domain].allowed
        return False

    def add_allow(self, domain: str, max_pages: int = 100, max_depth: int = 3, reason: str = "") -> None:
        """Add a domain to the allowlist."""
        self._rules[domain] = DomainRule(
            domain=domain, allowed=True,
            max_pages=max_pages, max_depth=max_depth, reason=reason,
        )
        self._save()

    def add_block(self, domain: str, reason: str = "") -> None:
        """Add a domain to the blocklist."""
        self._rules[domain] = DomainRule(
            domain=domain, allowed=False, reason=reason,
        )
        self._save()

    def remove(self, domain: str) -> bool:
        """Remove a domain rule."""
        if domain in self._rules:
            del self._rules[domain]
            self._save()
            return True
        return False

    def record_page(self, domain: str) -> None:
        """Record that a page from a domain was crawled."""
        self._page_counts[domain] = self._page_counts.get(domain, 0) + 1

    def get_page_count(self, domain: str) -> int:
        """Get the number of pages crawled from a domain."""
        return self._page_counts.get(domain, 0)

    def reset_counts(self) -> None:
        """Reset all page counts."""
        self._page_counts.clear()

    def list_rules(self) -> list[DomainRule]:
        """List all domain rules."""
        return list(self._rules.values())

    def get_max_depth(self, domain: str) -> int:
        """Get the max crawl depth for a domain."""
        if domain in self._rules:
            return self._rules[domain].max_depth
        return 3  # Default
