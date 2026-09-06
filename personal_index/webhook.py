"""Webhook notification system for external integrations."""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.error import URLError
from urllib.request import Request

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """WebhookEvent."""
    CRAWL_COMPLETE = "crawl_complete"
    CRAWL_FAILED = "crawl_failed"
    INDEX_UPDATE = "index_update"
    ERROR_OCCURRED = "error_occurred"
    HEALTH_CHECK = "health_check"
    BACKUP_COMPLETE = "backup_complete"


@dataclass
class WebhookPayload:
    """Payload sent to webhook endpoints."""

    event: WebhookEvent
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "personal-index"

    def to_dict(self) -> dict[str, Any]:
        """Return a new dict with exactly the keys ``event``, ``data``, ``timestamp``, ``source``.

        ``event`` is the enum's ``.value`` string (not the enum member);
        ``data``, ``timestamp``, and ``source`` are copied by reference.
        The payload object is NOT mutated.
        """
        return {
            "event": self.event.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    def to_json(self) -> str:
        """To_json."""
        return json.dumps(self.to_dict())


@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""

    url: str
    events: list[WebhookEvent] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0
    enabled: bool = True

    def should_send(self, event: WebhookEvent) -> bool:
        """Return whether this endpoint should receive the given event.

        Returns False when ``enabled`` is False (checked before any event
        matching). When enabled and ``events`` is empty, returns True for every
        event. Otherwise returns True only when ``event`` is a member of
        ``self.events``.
        """
        if not self.enabled:
            return False
        if not self.events:
            return True
        return event in self.events


class WebhookSender:
    """Sends webhook notifications to configured endpoints."""

    def __init__(self):
        self._configs: list[WebhookConfig] = []

    def add_endpoint(self, config: WebhookConfig) -> None:
        """Append a webhook endpoint config to the sender's endpoint list.

        Adds ``config`` to the internal ``_configs`` list in call order, with
        no URL validation or de-duplication. Returns None.
        """
        self._configs.append(config)

    def remove_endpoint(self, url: str) -> bool:
        """Remove the first endpoint whose URL matches, if any.

        Scans the internal ``_configs`` list in order; when a config's ``url``
        equals ``url``, removes that config and returns True. When no config
        matches, leaves the list unchanged and returns False.
        """
        for i, config in enumerate(self._configs):
            if config.url == url:
                self._configs.pop(i)
                return True
        return False

    def send(self, payload: WebhookPayload) -> list[dict]:
        """Send a webhook payload to all matching endpoints."""
        results = []
        for config in self._configs:
            if not config.should_send(payload.event):
                continue
            result = self._send_to_endpoint(config, payload)
            results.append(result)
        return results

    def _validate_url_scheme(self, url: str) -> str | None:
        """Validate URL scheme. Returns error message if invalid, None if valid."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"Unsupported URL scheme: {parsed.scheme}"
        return None

    def _build_request(self, config: WebhookConfig, payload: WebhookPayload) -> Request:
        """Build HTTP request from config and payload."""
        data = payload.to_json().encode("utf-8")
        return Request(
            config.url,
            data=data,
            headers={"Content-Type": "application/json", **config.headers},
            method="POST",
        )

    def _send_to_endpoint(self, config: WebhookConfig, payload: WebhookPayload) -> dict:
        scheme_error = self._validate_url_scheme(config.url)
        if scheme_error:
            return {
                "url": config.url,
                "status": None,
                "success": False,
                "error": scheme_error,
                "attempts": 0,
            }

        last_error = None
        for attempt in range(config.retry_count + 1):
            try:
                req = self._build_request(config, payload)
                with urllib.request.urlopen(req, timeout=config.timeout) as response:
                    return {
                        "url": config.url,
                        "status": response.status,
                        "success": True,
                        "attempts": attempt + 1,
                    }
            except (URLError, OSError, TimeoutError) as e:
                last_error = str(e)
                if attempt < config.retry_count:
                    time.sleep(config.retry_delay)

        return {
            "url": config.url,
            "status": None,
            "success": False,
            "error": last_error,
            "attempts": config.retry_count + 1,
        }

    @property
    def endpoint_count(self) -> int:
        """Endpoint_count."""
        return len(self._configs)
