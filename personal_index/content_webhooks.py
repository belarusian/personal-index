"""Webhook integration for personal-index content events.

Provides webhook registration, delivery, and retry logic
for notifying external services about content changes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WebhookEventType(Enum):
    """Types of webhook events."""

    CONTENT_ADDED = "content.added"
    CONTENT_UPDATED = "content.updated"
    CONTENT_DELETED = "content.deleted"
    BOOKMARK_ADDED = "bookmark.added"
    BOOKMARK_REMOVED = "bookmark.removed"
    TAG_ADDED = "tag.added"
    TAG_REMOVED = "tag.removed"
    CRAWL_STARTED = "crawl.started"
    CRAWL_COMPLETED = "crawl.completed"
    COLLECTION_CHANGED = "collection.changed"


@dataclass
class WebhookEndpoint:
    """A registered webhook endpoint.

    Attributes:
        endpoint_id: Unique identifier.
        url: Webhook URL.
        secret: Secret for signing payloads.
        events: Event types to subscribe to.
        enabled: Whether the endpoint is active.
        created_at: When the endpoint was registered.
        last_triggered: When the endpoint was last triggered.
        failure_count: Consecutive failure count.
        max_retries: Maximum retry attempts.
        retry_delay: Base delay between retries in seconds.
    """

    endpoint_id: str
    url: str
    secret: str | None = None
    events: list[WebhookEventType] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime | None = None
    last_triggered: datetime | None = None
    failure_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now()

    def should_retry(self) -> bool:
        """Check if the endpoint should retry after failures."""
        return self.failure_count < self.max_retries


@dataclass
class WebhookPayload:
    """A webhook payload to be delivered.

    Attributes:
        payload_id: Unique identifier.
        event_type: Type of event.
        data: Event data.
        endpoint_id: Target endpoint ID.
        url: Target URL.
        attempts: Number of delivery attempts.
        delivered: Whether delivery succeeded.
        delivered_at: When delivery succeeded.
        last_error: Last error message.
        signature: HMAC signature of the payload.
    """

    payload_id: str
    event_type: WebhookEventType
    data: dict[str, Any]
    endpoint_id: str
    url: str
    attempts: int = 0
    delivered: bool = False
    delivered_at: datetime | None = None
    last_error: str | None = None
    signature: str | None = None


class WebhookManager:
    """Manages webhook endpoints and payload delivery.

    Handles endpoint registration, event dispatching,
    payload signing, and retry logic.
    """

    def __init__(self) -> None:
        self.endpoints: dict[str, WebhookEndpoint] = {}
        self.pending: list[WebhookPayload] = []
        self.delivered: list[WebhookPayload] = []
        self._id_counter = 0

    def register_endpoint(
        self,
        url: str,
        events: list[WebhookEventType] | None = None,
        secret: str | None = None,
        **kwargs: Any,
    ) -> WebhookEndpoint:
        """Register a new webhook endpoint.

        Args:
            url: Webhook URL.
            events: Event types to subscribe to.
            secret: Secret for payload signing.
            **kwargs: Additional endpoint parameters.

        Returns:
            The registered WebhookEndpoint.
        """
        self._id_counter += 1
        endpoint_id = f"wh-{self._id_counter}"
        endpoint = WebhookEndpoint(
            endpoint_id=endpoint_id,
            url=url,
            secret=secret,
            events=events or list(WebhookEventType),
            **kwargs,
        )
        self.endpoints[endpoint_id] = endpoint
        return endpoint

    def remove_endpoint(self, endpoint_id: str) -> bool:
        """Remove a webhook endpoint."""
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            return True
        return False

    def dispatch_event(
        self,
        event_type: WebhookEventType,
        data: dict[str, Any],
    ) -> list[WebhookPayload]:
        """Dispatch an event to matching endpoints.

        Args:
            event_type: Type of event.
            data: Event data.

        Returns:
            List of created webhook payloads.
        """
        payloads = []

        for endpoint in self.endpoints.values():
            if not endpoint.enabled:
                continue
            if event_type not in endpoint.events:
                continue

            payload = self._create_payload(endpoint, event_type, data)
            self.pending.append(payload)
            payloads.append(payload)
            endpoint.last_triggered = datetime.now()

        return payloads

    def get_pending(self) -> list[WebhookPayload]:
        """Get all pending webhook payloads."""
        return self.pending

    def get_delivered(self) -> list[WebhookPayload]:
        """Get all delivered webhook payloads."""
        return self.delivered

    def mark_delivered(self, payload_id: str) -> bool:
        """Mark a payload as delivered."""
        for payload in self.pending:
            if payload.payload_id == payload_id:
                payload.delivered = True
                payload.delivered_at = datetime.now()
                self.pending.remove(payload)
                self.delivered.append(payload)
                # Reset failure count for endpoint
                endpoint = self.endpoints.get(payload.endpoint_id)
                if endpoint:
                    endpoint.failure_count = 0
                return True
        return False

    def mark_failed(self, payload_id: str, error: str) -> bool:
        """Mark a payload as failed and schedule retry if possible."""
        for payload in self.pending:
            if payload.payload_id == payload_id:
                payload.attempts += 1
                payload.last_error = error
                endpoint = self.endpoints.get(payload.endpoint_id)
                if endpoint:
                    endpoint.failure_count += 1
                    if not endpoint.should_retry():
                        self.pending.remove(payload)
                        self.delivered.append(payload)
                return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get webhook manager statistics."""
        return {
            "total_endpoints": len(self.endpoints),
            "enabled_endpoints": sum(
                1 for e in self.endpoints.values() if e.enabled,
            ),
            "pending_payloads": len(self.pending),
            "delivered_payloads": len(self.delivered),
        }

    def _create_payload(
        self,
        endpoint: WebhookEndpoint,
        event_type: WebhookEventType,
        data: dict[str, Any],
    ) -> WebhookPayload:
        """Create a webhook payload with optional signing."""
        payload_data = {
            "event": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        signature = None
        if endpoint.secret:
            body = json.dumps(payload_data, sort_keys=True)
            signature = self._sign(body, endpoint.secret)

        return WebhookPayload(
            payload_id=f"pl-{self._id_counter}-{int(time.time())}",
            event_type=event_type,
            data=data,
            endpoint_id=endpoint.endpoint_id,
            url=endpoint.url,
            signature=signature,
        )

    def _sign(self, body: str, secret: str) -> str:
        """Create HMAC signature for a payload."""
        return hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

    def get_payload_json(self, payload: WebhookPayload) -> str:
        """Get the JSON body for a payload."""
        return json.dumps({
            "event": payload.event_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": payload.data,
        }, sort_keys=True)
