"""Adversarial deep tests for personal_index/content_webhooks.py.

Targets the public surface of WebhookManager / WebhookEndpoint /
WebhookPayload: endpoint registration, event dispatch, HMAC signing,
payload-id idempotency, retry/backoff exhaustion, and the
get_payload_json round-trip contract.

QA-45: payload_id is documented as a "Unique identifier" but is built as
``pl-{counter}-{timestamp}`` where the counter only increments on
register_endpoint, so two dispatches to the same endpoint in the same
second collide and mark_delivered/mark_failed then act on the wrong
payload. Pinned with xfail-strict below.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from personal_index.content_webhooks import (
    WebhookEndpoint,
    WebhookEventType,
    WebhookManager,
    WebhookPayload,
)


@pytest.fixture
def mgr() -> WebhookManager:
    return WebhookManager()


# ---------------------------------------------------------------------------
# Endpoint registration
# ---------------------------------------------------------------------------
class TestRegisterEndpoint:
    def test_default_events_is_all_types(self, mgr):
        e = mgr.register_endpoint("http://x")
        assert set(e.events) == set(WebhookEventType)

    def test_none_events_defaults_to_all(self, mgr):
        e = mgr.register_endpoint("http://x", events=None)
        assert set(e.events) == set(WebhookEventType)

    def test_empty_events_list_defaults_to_all(self, mgr):
        # ``events or list(WebhookEventType)`` treats an empty list as
        # "no events specified" and falls back to subscribing to all types.
        e = mgr.register_endpoint("http://x", events=[])
        assert set(e.events) == set(WebhookEventType)

    def test_duplicate_url_allowed(self, mgr):
        e1 = mgr.register_endpoint("http://same")
        e2 = mgr.register_endpoint("http://same")
        assert e1.endpoint_id != e2.endpoint_id
        assert len(mgr.endpoints) == 2

    def test_unicode_url_round_trips(self, mgr):
        url = "http://\u0441\u043f\u0430\u0441\u0438\u0431\u0430.example/\u0434\u0437\u0435\u043d"
        e = mgr.register_endpoint(url)
        assert e.url == url

    def test_empty_url_accepted(self, mgr):
        e = mgr.register_endpoint("")
        assert e.url == ""

    def test_kwargs_forwarded(self, mgr):
        e = mgr.register_endpoint("http://x", max_retries=7, retry_delay=2.5)
        assert e.max_retries == 7
        assert e.retry_delay == 2.5

    def test_created_at_auto_set(self, mgr):
        e = mgr.register_endpoint("http://x")
        assert e.created_at is not None
        assert e.created_at.tzinfo is not None

    def test_remove_endpoint_present(self, mgr):
        e = mgr.register_endpoint("http://x")
        assert mgr.remove_endpoint(e.endpoint_id) is True
        assert e.endpoint_id not in mgr.endpoints

    def test_remove_endpoint_absent(self, mgr):
        assert mgr.remove_endpoint("wh-nope") is False


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
class TestDispatch:
    def test_disabled_endpoint_skipped(self, mgr):
        e = mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        e.enabled = False
        out = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        assert out == []
        assert mgr.get_pending() == []

    def test_unsubscribed_event_skipped(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        out = mgr.dispatch_event(WebhookEventType.TAG_ADDED, {"a": 1})
        assert out == []

    def test_empty_data_dispatched(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        out = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {})
        assert len(out) == 1
        assert out[0].data == {}

    def test_unicode_data_dispatched(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        out = mgr.dispatch_event(
            WebhookEventType.CONTENT_ADDED, {"text": "\u0441\u043f\u0430\u0441\u0438\u0431\u0430"}
        )
        assert out[0].data["text"] == "\u0441\u043f\u0430\u0441\u0438\u0431\u0430"

    def test_last_triggered_set_on_dispatch(self, mgr):
        e = mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        assert e.last_triggered is None
        mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        assert e.last_triggered is not None

    def test_non_serializable_data_raises(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        with pytest.raises(TypeError):
            mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"s": {1, 2, 3}})


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------
class TestSigning:
    def test_no_secret_no_signature(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        out = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        assert out[0].signature is None

    def test_empty_secret_string_no_signature(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED], secret="")
        out = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        assert out[0].signature is None

    def test_signature_matches_independent_hmac(self, mgr):
        mgr.register_endpoint(
            "http://x", [WebhookEventType.CONTENT_ADDED], secret="s3cr3t"
        )
        out = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        p = out[0]
        expected = hmac.new(
            b"s3cr3t", p.body.encode(), hashlib.sha256
        ).hexdigest()
        assert p.signature == expected

    def test_signature_over_exact_body(self, mgr):
        mgr.register_endpoint(
            "http://x", [WebhookEventType.CONTENT_ADDED], secret="k"
        )
        out = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        p = out[0]
        # The signature must be over the exact body string that will be
        # delivered (get_payload_json returns p.body unchanged).
        delivered = mgr.get_payload_json(p)
        assert delivered == p.body
        assert p.signature == hmac.new(
            b"k", delivered.encode(), hashlib.sha256
        ).hexdigest()


# ---------------------------------------------------------------------------
# Payload-id idempotency  (QA-45)
# ---------------------------------------------------------------------------
class TestPayloadIdUniqueness:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-45: payload_id is documented as a 'Unique identifier' but is "
            "built as pl-{counter}-{timestamp} where the counter only "
            "increments on register_endpoint; two dispatches to the same "
            "endpoint in the same second collide."
        ),
    )
    def test_payload_ids_unique_across_dispatches(self, mgr, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000.0)
        mgr.register_endpoint(
            "http://x",
            [WebhookEventType.CONTENT_ADDED, WebhookEventType.CONTENT_UPDATED],
        )
        p1 = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        p2 = mgr.dispatch_event(WebhookEventType.CONTENT_UPDATED, {"b": 2})
        assert p1[0].payload_id != p2[0].payload_id

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-45: with colliding payload_ids, mark_delivered on the shared "
            "id removes only the first pending payload, orphaning the second."
        ),
    )
    def test_mark_delivered_does_not_orphan_twin(self, mgr, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1000.0)
        mgr.register_endpoint(
            "http://x",
            [WebhookEventType.CONTENT_ADDED, WebhookEventType.CONTENT_UPDATED],
        )
        p1 = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        p2 = mgr.dispatch_event(WebhookEventType.CONTENT_UPDATED, {"b": 2})
        assert p1[0].payload_id == p2[0].payload_id  # the collision
        mgr.mark_delivered(p1[0].payload_id)
        # Both payloads should be accounted for; the twin must not be left
        # stranded in pending under an id that no longer resolves uniquely.
        assert len(mgr.get_pending()) == 0


# ---------------------------------------------------------------------------
# Retry / backoff / exhaustion
# ---------------------------------------------------------------------------
class TestRetryExhaustion:
    def test_failure_schedules_retry(self, mgr):
        e = mgr.register_endpoint(
            "http://x", [WebhookEventType.CONTENT_ADDED], max_retries=3,
            retry_delay=1.0,
        )
        p = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})[0]
        assert mgr.mark_failed(p.payload_id, "boom") is True
        assert p.attempts == 1
        assert p.last_error == "boom"
        assert e.failure_count == 1
        assert p.next_retry_at is not None
        assert p in mgr.get_pending()

    def test_exhaustion_drops_to_delivered(self, mgr):
        e = mgr.register_endpoint(
            "http://x", [WebhookEventType.CONTENT_ADDED], max_retries=3,
        )
        p = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})[0]
        for _ in range(3):
            assert mgr.mark_failed(p.payload_id, "boom") is True
        assert p not in mgr.get_pending()
        assert p in mgr.get_delivered()
        assert p.next_retry_at is None
        assert e.failure_count == 3
        assert e.should_retry() is False

    def test_mark_failed_absent_returns_false(self, mgr):
        assert mgr.mark_failed("pl-nope", "x") is False

    def test_mark_delivered_resets_failure_count(self, mgr):
        e = mgr.register_endpoint(
            "http://x", [WebhookEventType.CONTENT_ADDED], max_retries=3,
        )
        p = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})[0]
        mgr.mark_failed(p.payload_id, "boom")
        assert e.failure_count == 1
        assert mgr.mark_delivered(p.payload_id) is True
        assert e.failure_count == 0
        assert p in mgr.get_delivered()

    def test_mark_delivered_absent_returns_false(self, mgr):
        assert mgr.mark_delivered("pl-nope") is False

    def test_should_retry_boundary(self):
        e = WebhookEndpoint(endpoint_id="e", url="u", max_retries=3)
        e.failure_count = 2
        assert e.should_retry() is True
        e.failure_count = 3
        assert e.should_retry() is False


# ---------------------------------------------------------------------------
# get_payload_json round-trip
# ---------------------------------------------------------------------------
class TestGetPayloadJson:
    def test_body_returned_unchanged(self, mgr):
        body = '{"data":{"x":1},"event":"content.added","timestamp":"2026-01-01T00:00:00Z"}'
        p = WebhookPayload(
            payload_id="p1", event_type=WebhookEventType.CONTENT_ADDED,
            data={"x": 1}, endpoint_id="e1", url="http://x", body=body,
        )
        assert mgr.get_payload_json(p) == body

    def test_body_none_falls_back(self, mgr):
        p = WebhookPayload(
            payload_id="p2", event_type=WebhookEventType.CONTENT_ADDED,
            data={"x": 1}, endpoint_id="e1", url="http://x", body=None,
        )
        out = mgr.get_payload_json(p)
        assert "content.added" in out
        assert '"x"' in out
        # Fallback must be valid JSON.
        json.loads(out)

    def test_dispatched_payload_body_is_valid_json(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        p = mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})[0]
        parsed = json.loads(mgr.get_payload_json(p))
        assert parsed["event"] == "content.added"
        assert parsed["data"] == {"a": 1}
        assert "timestamp" in parsed

    def test_unicode_body_round_trips(self, mgr):
        mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        p = mgr.dispatch_event(
            WebhookEventType.CONTENT_ADDED, {"t": "\u0441\u043f\u0430\u0441\u0438\u0431\u0430"}
        )[0]
        parsed = json.loads(mgr.get_payload_json(p))
        assert parsed["data"]["t"] == "\u0441\u043f\u0430\u0441\u0438\u0431\u0430"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
class TestStats:
    def test_empty_stats(self, mgr):
        s = mgr.get_stats()
        assert s == {
            "total_endpoints": 0,
            "enabled_endpoints": 0,
            "pending_payloads": 0,
            "delivered_payloads": 0,
        }

    def test_stats_counts(self, mgr):
        e = mgr.register_endpoint("http://x", [WebhookEventType.CONTENT_ADDED])
        mgr.register_endpoint("http://y", [WebhookEventType.CONTENT_ADDED])
        e.enabled = False
        mgr.dispatch_event(WebhookEventType.CONTENT_ADDED, {"a": 1})
        s = mgr.get_stats()
        assert s["total_endpoints"] == 2
        assert s["enabled_endpoints"] == 1
        assert s["pending_payloads"] == 1
        assert s["delivered_payloads"] == 0
