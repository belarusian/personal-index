"""Domain management for crawling rules."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DomainRule:
    """Rule for a specific domain."""

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
        return cls(**data)


@dataclass
class DomainManager:
    """Manages domain allow/block rules."""

    rules_file: Optional[str] = None
    _rules: Dict[str, DomainRule] = field(default_factory=dict, repr=False)
    _page_counts: Dict[str, int] = field(default_factory=dict, repr=False)
    _has_whitelist: bool = False

    def __post_init__(self):
        if self.rules_file and os.path.exists(self.rules_file):
            self._load()

    def _load(self) -> None:
        try:
            with open(self.rules_file, "r") as f:
                data = json.load(f)
            self._rules = {d: DomainRule.from_dict(r) for d, r in data.items()}
            self._has_whitelist = any(r.allowed for r in self._rules.values())
        except (json.JSONDecodeError, KeyError):
            self._rules = {}

    def _save(self) -> None:
        if not self.rules_file:
            return
        os.makedirs(os.path.dirname(self.rules_file) or ".", exist_ok=True)
        data = {d: r.to_dict() for d, r in self._rules.items()}
        with open(self.rules_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_allow(self, domain: str, max_pages: int = 100, max_depth: int = 3) -> None:
        self._rules[domain] = DomainRule(domain=domain, allowed=True, max_pages=max_pages, max_depth=max_depth)
        self._has_whitelist = True
        self._save()

    def add_block(self, domain: str, reason: str = "") -> None:
        self._rules[domain] = DomainRule(domain=domain, allowed=False, reason=reason)
        self._save()

    def is_allowed(self, domain: str) -> bool:
        if domain in self._rules:
            rule = self._rules[domain]
            if not rule.allowed:
                return False
            if self._page_counts.get(domain, 0) >= rule.max_pages:
                return False
            return True
        if self._has_whitelist:
            return False
        return True

    def is_blocked(self, domain: str) -> bool:
        if domain in self._rules:
            return not self._rules[domain].allowed
        return False

    def record_page(self, domain: str) -> None:
        self._page_counts[domain] = self._page_counts.get(domain, 0) + 1

    def get_page_count(self, domain: str) -> int:
        return self._page_counts.get(domain, 0)

    def reset_counts(self) -> None:
        self._page_counts = {}

    def remove(self, domain: str) -> bool:
        if domain in self._rules:
            del self._rules[domain]
            self._save()
            return True
        return False

    def list_rules(self) -> List[DomainRule]:
        return list(self._rules.values())

    def get_max_depth(self, domain: str) -> int:
        if domain in self._rules:
            return self._rules[domain].max_depth
        return 3
