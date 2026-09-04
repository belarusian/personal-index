"""Tests for the content webhooks module."""

from personal_index.content_webhooks import (
    WebhookEndpoint,
    WebhookEventType,
    WebhookManager,
)


class TestWebhookEndpoint:
    def test_create(self) -> None:
        endpoint = WebhookEndpoint(
            endpoint_id="wh-1",
            url="https://example.com/webhook",
        )
        assert endpoint.enabled is True
        assert endpoint.failure_count == 0

    def test_should_retry(self) -> None:
        endpoint = WebhookEndpoint(
            endpoint_id="wh-1",
            url="https://example.com/webhook",
            max_retries=3,
        )
        assert endpoint.should_retry() is True
        endpoint.failure_count = 2
        assert endpoint.should_retry() is True
        endpoint.failure_count = 3
        assert endpoint.should_retry() is False


class TestWebhookManager:
    def setup_method(self) -> None:
        self.manager = WebhookManager()

    def test_register_endpoint(self) -> None:
        endpoint = self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        assert endpoint.endpoint_id
        assert endpoint.url == "https://example.com/webhook"

    def test_remove_endpoint(self) -> None:
        self.manager.register_endpoint("https://example.com/webhook")
        endpoints = list(self.manager.endpoints.keys())
        assert self.manager.remove_endpoint(endpoints[0]) is True
        assert len(self.manager.endpoints) == 0

    def test_dispatch_event(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 1
        assert payloads[0].event_type == WebhookEventType.CONTENT_ADDED

    def test_dispatch_event_no_match(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.BOOKMARK_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 0

    def test_dispatch_disabled_endpoint(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
            enabled=False,
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 0

    def test_dispatch_all_events(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 1

    def test_mark_delivered(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        payload_id = payloads[0].payload_id
        assert self.manager.mark_delivered(payload_id) is True
        assert len(self.manager.get_pending()) == 0
        assert len(self.manager.get_delivered()) == 1

    def test_mark_failed(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
            max_retries=1,
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        payload_id = payloads[0].payload_id
        assert self.manager.mark_failed(payload_id, "Connection error") is True
        assert len(self.manager.get_pending()) == 0

    def test_mark_failed_no_retry_scheduling_docstring(self) -> None:
        import inspect
        src = inspect.getsource(self.manager.mark_failed)
        assert "schedule retry" not in src

    def test_mark_failed_moves_to_delivered_when_retries_exhausted(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
            max_retries=1,
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        payload_id = payloads[0].payload_id
        assert self.manager.mark_failed(payload_id, "Connection error") is True
        assert len(self.manager.get_pending()) == 0
        assert len(self.manager.get_delivered()) == 1

    def test_payload_signing(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
            secret="my-secret",
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert payloads[0].signature is not None
        assert len(payloads[0].signature) == 64  # SHA-256 hex

    def test_get_stats(self) -> None:
        self.manager.register_endpoint("https://example.com/webhook")
        stats = self.manager.get_stats()
        assert stats["total_endpoints"] == 1
        assert stats["enabled_endpoints"] == 1

    def test_get_payload_json(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        json_str = self.manager.get_payload_json(payloads[0])
        assert "content.added" in json_str
        assert "New Content" in json_str

    def test_multiple_endpoints(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/hook1",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        self.manager.register_endpoint(
            "https://example.com/hook2",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 2
