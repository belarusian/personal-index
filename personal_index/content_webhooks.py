"""Content webhooks - notify on new saves."""

from __future__ import annotations

import uuid
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


class SaveEventType(str, Enum):
    """Types of save events that trigger webhooks."""
    ITEM_SAVED = "item_saved"
    ITEM_UPDATED = "item_updated"
    ITEM_DELETED = "item_deleted"
    CRAWL_STARTED = "crawl_started"
    CRAWL_COMPLETED = "crawl_completed"
    TAG_ADDED = "tag_added"


class WebhookDeliveryStatus(str, Enum):
    """Status of a webhook delivery attempt."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SaveEvent:
    """An event triggered by a save action."""
    event_type: SaveEventType
    url: str
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "url": self.url,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def to_payload(self) -> dict:
        """Create the full webhook payload."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "url": self.url,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "source": "personal-index",
        }


@dataclass
class WebhookSubscription:
    """A webhook subscription for save events."""
    url: str
    events: list[SaveEventType] = field(default_factory=list)
    headers: dict = field(default_factory=dict)
    subscription_id: str = field(
        default_factory=lambda: uuid.uuid4().hex[:12]
    )
    enabled: bool = True
    timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def should_trigger(self, event_type: SaveEventType) -> bool:
        """Check if this subscription should trigger for the given event."""
        if not self.enabled:
            return False
        if not self.events:
            return True
        return event_type in self.events

    def to_dict(self) -> dict:
        return {
            "subscription_id": self.subscription_id,
            "url": self.url,
            "events": [e.value for e in self.events],
            "enabled": self.enabled,
            "headers": self.headers,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
        }


@dataclass
class WebhookDelivery:
    """Records a single webhook delivery attempt."""
    subscription_id: str
    event_id: str
    delivery_id: str = field(
        default_factory=lambda: uuid.uuid4().hex[:12]
    )
    status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING
    status_code: Optional[int] = None
    error: str = ""
    attempts: int = 0
    delivered_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def mark_sent(self, status_code: int) -> None:
        """Mark delivery as successfully sent."""
        self.status = WebhookDeliveryStatus.SENT
        self.status_code = status_code
        self.delivered_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str) -> None:
        """Mark delivery as failed."""
        self.status = WebhookDeliveryStatus.FAILED
        self.error = error

    def to_dict(self) -> dict:
        return {
            "delivery_id": self.delivery_id,
            "subscription_id": self.subscription_id,
            "event_id": self.event_id,
            "status": self.status.value,
            "status_code": self.status_code,
            "error": self.error,
            "attempts": self.attempts,
            "delivered_at": self.delivered_at,
            "created_at": self.created_at,
        }


class WebhookDispatcher:
    """Dispatches webhook notifications for save events."""

    def __init__(self):
        self._subscriptions: dict[str, WebhookSubscription] = {}
        self._deliveries: dict[str, list[WebhookDelivery]] = {}

    def add_subscription(self, subscription: WebhookSubscription) -> None:
        """Add a webhook subscription."""
        self._subscriptions[subscription.subscription_id] = subscription
        self._deliveries[subscription.subscription_id] = []

    def remove_subscription(self, subscription_id: str) -> bool:
        """Remove a webhook subscription."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            del self._deliveries[subscription_id]
            return True
        return False

    def dispatch(self, event: SaveEvent) -> list[WebhookDelivery]:
        """Dispatch an event to all matching subscriptions."""
        deliveries = []
        for sub in self._subscriptions.values():
            if not sub.should_trigger(event.event_type):
                continue
            delivery = self._deliver(sub, event)
            deliveries.append(delivery)
            self._deliveries[sub.subscription_id].append(delivery)
        return deliveries

    def _deliver(
        self,
        subscription: WebhookSubscription,
        event: SaveEvent,
    ) -> WebhookDelivery:
        """Deliver an event to a single subscription."""
        delivery = WebhookDelivery(
            subscription_id=subscription.subscription_id,
            event_id=event.event_id,
        )

        payload = json.dumps(event.to_payload()).encode("utf-8")
        last_error = None

        for attempt in range(subscription.max_retries + 1):
            delivery.attempts = attempt + 1
            try:
                req = Request(
                    subscription.url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Event-Type": event.event_type.value,
                        "X-Event-ID": event.event_id,
                        **subscription.headers,
                    },
                    method="POST",
                )
                with urlopen(req, timeout=subscription.timeout) as response:
                    delivery.mark_sent(response.status)
                    return delivery
            except Exception as e:
                last_error = str(e)
                if attempt < subscription.max_retries:
                    delivery.status = WebhookDeliveryStatus.RETRYING
                    time.sleep(subscription.retry_delay)

        delivery.mark_failed(last_error or "Unknown error")
        return delivery

    def get_deliveries(self, subscription_id: str) -> list[WebhookDelivery]:
        """Get delivery history for a subscription."""
        return list(self._deliveries.get(subscription_id, []))

    @property
    def subscriptions(self) -> list[WebhookSubscription]:
        return list(self._subscriptions.values())

    @property
    def subscription_count(self) -> int:
        return len(self._subscriptions)
