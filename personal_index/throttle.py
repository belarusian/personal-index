"""Request throttling with per-domain rate limiting."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ThrottleRule:
    """Rate limiting rule for a domain."""

    max_requests: int = 10
    window_seconds: float = 60.0
    min_delay: float = 0.5

    @property
    def rate_per_second(self) -> float:
        """Rate_per_second."""
        return self.max_requests / self.window_seconds


@dataclass
class ThrottleState:
    """Tracks throttle state for a domain."""

    request_times: list[float] = field(default_factory=list)
    last_request: Optional[float] = None
    total_requests: int = 0
    total_wait_time: float = 0.0


class ThrottleManager:
    """Manages request throttling across multiple domains."""

    def __init__(self, default_rule: Optional[ThrottleRule] = None):
        self._rules: dict[str, ThrottleRule] = {}
        self._states: dict[str, ThrottleState] = {}
        self._default_rule = default_rule or ThrottleRule()

    def set_rule(self, domain: str, rule: ThrottleRule) -> None:
        """Process set_rule.

        Args:
        domain, rule.
        """
        self._rules[domain] = rule

    def get_rule(self, domain: str) -> ThrottleRule:
        """Process get_rule.

        Args:
        domain.
        """
        return self._rules.get(domain, self._default_rule)

    def should_throttle(self, url: str) -> bool:
        """Process should_throttle.

        Args:
        url.
        """
        domain = self._extract_domain(url)
        rule = self.get_rule(domain)
        state = self._states.setdefault(domain, ThrottleState())

        now = time.time()
        cutoff = now - rule.window_seconds
        state.request_times = [t for t in state.request_times if t > cutoff]

        return len(state.request_times) >= rule.max_requests

    def wait_if_needed(self, url: str) -> float:
        """Wait if throttling is needed, return wait time in seconds."""
        domain = self._extract_domain(url)
        rule = self.get_rule(domain)
        state = self._states.setdefault(domain, ThrottleState())

        now = time.time()
        wait_time = 0.0

        if state.last_request is not None:
            elapsed = now - state.last_request
            min_wait = 1.0 / rule.rate_per_second if rule.rate_per_second > 0 else rule.min_delay
            if elapsed < min_wait:
                wait_time = min_wait - elapsed

        if self.should_throttle(url):
            oldest = state.request_times[0] if state.request_times else now
            window_wait = (oldest + rule.window_seconds) - now
            wait_time = max(wait_time, window_wait, rule.min_delay)

        if wait_time > 0:
            time.sleep(wait_time)
            state.total_wait_time += wait_time

        self._record_request(domain, state)
        return wait_time

    def _record_request(self, domain: str, state: ThrottleState) -> None:
        now = time.time()
        state.request_times.append(now)
        state.last_request = now
        state.total_requests += 1

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or url

    def get_stats(self, domain: Optional[str] = None) -> dict:
        """Process get_stats.

        Args:
        domain.
        """
        if domain:
            state = self._states.get(domain)
            if state:
                return {
                    "domain": domain,
                    "total_requests": state.total_requests,
                    "total_wait_time": state.total_wait_time,
                    "rule": self.get_rule(domain).__dict__,
                }
            return {"domain": domain, "total_requests": 0}

        return {
            "domains_tracked": len(self._states),
            "total_requests": sum(s.total_requests for s in self._states.values()),
            "total_wait_time": sum(s.total_wait_time for s in self._states.values()),
        }

    def reset(self, domain: Optional[str] = None) -> None:
        """Reset throttle counters.

        Args:
            domain: Specific domain to reset, or None for all.
        """
        if domain:
            self._states.pop(domain, None)
        else:
            self._states.clear()
