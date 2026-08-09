"""Tests for content_webhooks module - notify on new saves."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from personal_index.content_webhooks import (
    SaveEvent,
    SaveEventType,
    WebhookSubscription,
    WebhookDispatcher,
    WebhookDelivery,
    WebhookDeliveryStatus,
)


class TestSaveEventType:
    """Tests for SaveEventType enum."""

    def test_event_types(self):
        assert SaveEventType.ITEM_SAVED.value == "item_saved"
        assert SaveEventType.ITEM_UPDATED.value == "item_updated"
        assert SaveEventType.ITEM_DELETED.value == "item_deleted"
        assert SaveEventType.CRAWL_STARTED.value == "crawl_started"
        assert SaveEventType.CRAWL_COMPLETED.value == "crawl_completed"
        assert SaveEventType.TAG_ADDED.value == "tag_added"


class TestSaveEvent:
    """Tests for SaveEvent model."""

    def test_create_event(self):
        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )
        assert event.event_type == SaveEventType.ITEM_SAVED
        assert event.url == "https://example.com/page"
        assert event.event_id is not None

    def test_event_with_metadata(self):
        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
            metadata={"title": "Test Page", "tags": ["tech"]},
        )
        assert event.metadata["title"] == "Test Page"

    def test_event_to_dict(self):
        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )
        d = event.to_dict()
        assert d["event_type"] == SaveEventType.ITEM_SAVED.value
        assert d["url"] == "https://example.com/page"

    def test_event_to_payload(self):
        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )
        payload = event.to_payload()
        assert "event_type" in payload
        assert "url" in payload
        assert "timestamp" in payload
        assert "event_id" in payload


class TestWebhookSubscription:
    """Tests for WebhookSubscription model."""

    def test_create_subscription(self):
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        )
        assert sub.url == "https://hooks.example.com/webhook"
        assert SaveEventType.ITEM_SAVED in sub.events
        assert sub.enabled is True

    def test_subscription_with_headers(self):
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            headers={"Authorization": "Bearer token123"},
        )
        assert sub.headers["Authorization"] == "Bearer token123"

    def test_subscription_should_trigger(self):
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        )
        assert sub.should_trigger(SaveEventType.ITEM_SAVED) is True
        assert sub.should_trigger(SaveEventType.ITEM_DELETED) is False

    def test_subscription_all_events(self):
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[],
        )
        assert sub.should_trigger(SaveEventType.ITEM_SAVED) is True
        assert sub.should_trigger(SaveEventType.ITEM_DELETED) is True

    def test_subscription_disabled(self):
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            enabled=False,
        )
        assert sub.should_trigger(SaveEventType.ITEM_SAVED) is False

    def test_subscription_to_dict(self):
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        )
        d = sub.to_dict()
        assert d["url"] == "https://hooks.example.com/webhook"


class TestWebhookDelivery:
    """Tests for WebhookDelivery model."""

    def test_create_delivery(self):
        delivery = WebhookDelivery(
            subscription_id="sub1",
            event_id="evt1",
        )
        assert delivery.subscription_id == "sub1"
        assert delivery.event_id == "evt1"
        assert delivery.status == WebhookDeliveryStatus.PENDING

    def test_delivery_mark_sent(self):
        delivery = WebhookDelivery(subscription_id="sub1", event_id="evt1")
        delivery.mark_sent(status_code=200)
        assert delivery.status == WebhookDeliveryStatus.SENT
        assert delivery.status_code == 200

    def test_delivery_mark_failed(self):
        delivery = WebhookDelivery(subscription_id="sub1", event_id="evt1")
        delivery.mark_failed(error="timeout")
        assert delivery.status == WebhookDeliveryStatus.FAILED
        assert delivery.error == "timeout"

    def test_delivery_to_dict(self):
        delivery = WebhookDelivery(subscription_id="sub1", event_id="evt1")
        d = delivery.to_dict()
        assert d["subscription_id"] == "sub1"
        assert d["event_id"] == "evt1"


class TestWebhookDeliveryStatus:
    """Tests for WebhookDeliveryStatus enum."""

    def test_status_values(self):
        assert WebhookDeliveryStatus.PENDING.value == "pending"
        assert WebhookDeliveryStatus.SENT.value == "sent"
        assert WebhookDeliveryStatus.FAILED.value == "failed"
        assert WebhookDeliveryStatus.RETRYING.value == "retrying"


class TestWebhookDispatcher:
    """Tests for WebhookDispatcher class."""

    def test_init(self):
        dispatcher = WebhookDispatcher()
        assert len(dispatcher.subscriptions) == 0

    def test_add_subscription(self):
        dispatcher = WebhookDispatcher()
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        )
        dispatcher.add_subscription(sub)
        assert len(dispatcher.subscriptions) == 1

    def test_remove_subscription(self):
        dispatcher = WebhookDispatcher()
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        )
        dispatcher.add_subscription(sub)
        dispatcher.remove_subscription(sub.subscription_id)
        assert len(dispatcher.subscriptions) == 0

    def test_dispatch_event(self):
        dispatcher = WebhookDispatcher()
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        )
        dispatcher.add_subscription(sub)

        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )

        with patch("personal_index.content_webhooks.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            deliveries = dispatcher.dispatch(event)
            assert len(deliveries) == 1
            assert deliveries[0].status == WebhookDeliveryStatus.SENT

    def test_dispatch_skips_disabled(self):
        dispatcher = WebhookDispatcher()
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
            enabled=False,
        )
        dispatcher.add_subscription(sub)

        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )

        with patch("personal_index.content_webhooks.urlopen") as mock_urlopen:
            deliveries = dispatcher.dispatch(event)
            assert len(deliveries) == 0
            mock_urlopen.assert_not_called()

    def test_dispatch_retry_on_failure(self):
        dispatcher = WebhookDispatcher()
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
            max_retries=2,
            retry_delay=0.01,
        )
        dispatcher.add_subscription(sub)

        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )

        with patch("personal_index.content_webhooks.urlopen", side_effect=Exception("fail")):
            with patch("personal_index.content_webhooks.time.sleep"):
                deliveries = dispatcher.dispatch(event)
                assert len(deliveries) == 1
                assert deliveries[0].status == WebhookDeliveryStatus.FAILED

    def test_dispatch_multiple_subscriptions(self):
        dispatcher = WebhookDispatcher()
        dispatcher.add_subscription(WebhookSubscription(
            url="https://hook1.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        ))
        dispatcher.add_subscription(WebhookSubscription(
            url="https://hook2.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        ))

        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )

        with patch("personal_index.content_webhooks.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            deliveries = dispatcher.dispatch(event)
            assert len(deliveries) == 2

    def test_dispatch_event_type_filter(self):
        dispatcher = WebhookDispatcher()
        dispatcher.add_subscription(WebhookSubscription(
            url="https://hook1.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        ))

        event = SaveEvent(
            event_type=SaveEventType.ITEM_DELETED,
            url="https://example.com/page",
        )

        with patch("personal_index.content_webhooks.urlopen") as mock_urlopen:
            deliveries = dispatcher.dispatch(event)
            assert len(deliveries) == 0
            mock_urlopen.assert_not_called()

    def test_get_deliveries(self):
        dispatcher = WebhookDispatcher()
        sub = WebhookSubscription(
            url="https://hooks.example.com/webhook",
            events=[SaveEventType.ITEM_SAVED],
        )
        dispatcher.add_subscription(sub)

        event = SaveEvent(
            event_type=SaveEventType.ITEM_SAVED,
            url="https://example.com/page",
        )

        with patch("personal_index.content_webhooks.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            dispatcher.dispatch(event)
            deliveries = dispatcher.get_deliveries(sub.subscription_id)
            assert len(deliveries) == 1

    def test_subscription_count(self):
        dispatcher = WebhookDispatcher()
        dispatcher.add_subscription(WebhookSubscription(
            url="https://hook1.com/webhook",
        ))
        dispatcher.add_subscription(WebhookSubscription(
            url="https://hook2.com/webhook",
        ))
        assert dispatcher.subscription_count == 2
