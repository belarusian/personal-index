"""Webhook notification system for external integrations."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.request import Request, urlopen

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
        """To_dict."""
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
        """Process should_send.

        Args:
        event.
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
        """Process add_endpoint.

        Args:
        config.
        """
        self._configs.append(config)

    def remove_endpoint(self, url: str) -> bool:
        """Process remove_endpoint.

        Args:
        url.
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

    def _send_to_endpoint(self, config: WebhookConfig, payload: WebhookPayload) -> dict:
        last_error = None
        for attempt in range(config.retry_count + 1):
            try:
                data = payload.to_json().encode("utf-8")
                req = Request(
                    config.url,
                    data=data,
                    headers={"Content-Type": "application/json", **config.headers},
                    method="POST",
                )
                with urlopen(req, timeout=config.timeout) as response:
                    return {
                        "url": config.url,
                        "status": response.status,
                        "success": True,
                        "attempts": attempt + 1,
                    }
            except Exception as e:
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
