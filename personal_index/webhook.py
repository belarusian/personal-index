"""Webhook notification system for external integrations."""

from __future__ import annotations

import hashlib
import hmac
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
        """Return the payload as a dict with exactly four keys.

        Keys: ``event`` (the WebhookEvent's ``.value`` string, not the
        enum object), ``data`` (the payload dict), ``timestamp`` (float),
        ``source`` (str).
        """
        return {
            "event": self.event.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    def to_json(self) -> str:
        """Return the JSON string of ``self.to_dict()`` (json.dumps)."""
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
    secret: str | None = None

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
    """Sends webhook notifications to configured endpoints.

    Mirrors the live twin ``content_webhooks.WebhookManager`` record-and-track
    + HMAC contract: every ``send()`` records each matching endpoint's payload
    in a persistent ``pending`` store, moves it to ``delivered`` on success,
    and signs the body with the endpoint's ``secret`` (HMAC-SHA256) when one is
    set. Delivery history is queryable via ``get_pending()`` /
    ``get_delivered()`` / ``get_stats()``.
    """

    def __init__(self):
        self._configs: list[WebhookConfig] = []
        self.pending: list[WebhookPayload] = []
        self.delivered: list[WebhookPayload] = []

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
        """Send a webhook payload to all matching endpoints.

        Records each matching endpoint's payload in the persistent ``pending``
        store before dispatching, and moves it to ``delivered`` when the
        endpoint reports success (leaving it in ``pending`` on failure).
        Returns the transient per-endpoint result list (unchanged shape).
        """
        results = []
        for config in self._configs:
            if not config.should_send(payload.event):
                continue
            self.pending.append(payload)
            result = self._send_to_endpoint(config, payload)
            if result.get("success"):
                self.pending.remove(payload)
                self.delivered.append(payload)
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
        """Build HTTP request from config and payload.

        Signs the JSON body with the endpoint's ``secret`` (HMAC-SHA256) and
        attaches it as the ``X-Signature`` header when a secret is set; when no
        secret is configured the body is sent unsigned (no signature header).
        """
        body = payload.to_json()
        headers = {"Content-Type": "application/json", **config.headers}
        if config.secret:
            headers["X-Signature"] = self._sign(body, config.secret)
        return Request(
            config.url,
            data=body.encode("utf-8"),
            headers=headers,
            method="POST",
        )

    def _sign(self, body: str, secret: str) -> str:
        """Create an HMAC-SHA256 signature for a payload body.

        Returns the hex digest of ``hmac.new(secret, body, sha256)`` — the
        same construction as the live twin ``content_webhooks.WebhookManager._sign``.
        """
        return hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

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
        """Return the number of configured endpoints (len of the config list)."""
        return len(self._configs)

    def get_pending(self) -> list[WebhookPayload]:
        """Return the list of payloads still pending delivery (not yet delivered)."""
        return self.pending

    def get_delivered(self) -> list[WebhookPayload]:
        """Return the list of payloads delivered to at least one endpoint."""
        return self.delivered

    def get_stats(self) -> dict[str, Any]:
        """Return delivery-tracking statistics.

        Returns a dict with ``total_endpoints`` (configured endpoint count),
        ``enabled_endpoints`` (endpoints whose ``enabled`` is True),
        ``pending_payloads`` (len of the pending store), and
        ``delivered_payloads`` (len of the delivered store) — mirroring the
        live twin ``content_webhooks.WebhookManager.get_stats``.
        """
        return {
            "total_endpoints": len(self._configs),
            "enabled_endpoints": sum(
                (1 for c in self._configs if c.enabled),
            ),
            "pending_payloads": len(self.pending),
            "delivered_payloads": len(self.delivered),
        }
