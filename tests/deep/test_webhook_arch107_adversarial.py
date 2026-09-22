"""Adversarial deep tests for personal_index/webhook.py — ARCH-107 contract.

Cycle 354 (VALIDATOR) PROBE. webhook.py source changed 2026-09-17 (ARCH-107:
align WebhookSender to the live twin content_webhooks.WebhookManager —
persistent pending/delivered stores + get_stats + HMAC-SHA256 _sign), but the
existing deep test tests/deep/test_webhook_adversarial.py predates that change
(2026-09-15) and covers NONE of the new surface: _sign, get_pending,
get_delivered, get_stats, or the X-signature request header.

These pins re-derive every assertion against the ACTUAL result shape on current
main (probed live, not the defect-era shape). The probe found NO contract
violation: every behavior matches the documented contract, so all pins are hard
passes (regression armor). No xfail markers.

Contract under test (from webhook.py docstrings):
  - _sign(body, secret) == hmac.new(secret, body, sha256).hexdigest()
  - _build_request attaches X-signature (HMAC) header iff config.secret is set;
    body is payload.to_json(); method POST.
  - send() records each matching endpoint's payload in pending before dispatch,
    moves it to delivered on success, leaves it in pending on failure.
  - get_stats() -> {total_endpoints, enabled_endpoints, pending_payloads,
    delivered_payloads}.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from personal_index.webhook import (
    WebhookConfig,
    WebhookEvent,
    WebhookPayload,
    WebhookSender,
)


def _ok_response() -> MagicMock:
    m = MagicMock()
    m.status = 200
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    return m


def _sig(body: str, secret: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# _sign: HMAC-SHA256 construction
# ---------------------------------------------------------------------------
class TestSign:
    def test_matches_hmac_sha256_construction(self) -> None:
        s = WebhookSender()
        body = '{"event":"crawl_complete","data":{},"timestamp":1.0,"source":"personal-index"}'
        secret = "s3cr3t"
        assert s._sign(body, secret) == _sig(body, secret)

    def test_returns_64_char_hexdigest(self) -> None:
        s = WebhookSender()
        sig = s._sign("hello", "k")
        assert len(sig) == 64
        int(sig, 16)  # valid hex

    def test_empty_body(self) -> None:
        s = WebhookSender()
        assert s._sign("", "k") == _sig("", "k")

    def test_empty_secret(self) -> None:
        s = WebhookSender()
        assert s._sign("body", "") == _sig("body", "")

    def test_unicode_body(self) -> None:
        s = WebhookSender()
        body = "héllo→世界"
        assert s._sign(body, "s") == _sig(body, "s")

    def test_deterministic(self) -> None:
        s = WebhookSender()
        assert s._sign("x", "y") == s._sign("x", "y")

    def test_differs_by_body(self) -> None:
        s = WebhookSender()
        assert s._sign("a", "k") != s._sign("b", "k")

    def test_differs_by_secret(self) -> None:
        s = WebhookSender()
        assert s._sign("a", "k1") != s._sign("a", "k2")

    def test_matches_live_twin_construction(self) -> None:
        # The docstring claims the same construction as
        # content_webhooks.WebhookManager._sign. Pin the exact hmac call.
        s = WebhookSender()
        body, secret = "payload", "topsecret"
        expected = hmac.new(
            secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        assert s._sign(body, secret) == expected


# ---------------------------------------------------------------------------
# _build_request: X-signature header + body + method
# ---------------------------------------------------------------------------
class TestBuildRequest:
    def test_signature_header_present_when_secret_set(self) -> None:
        s = WebhookSender()
        secret = "s3cr3t"
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, timestamp=1.0)
        req = s._build_request(
            WebhookConfig(url="https://x.com", secret=secret), p
        )
        # urllib normalizes the header key to lower-case-with-dash.
        headers = dict(req.header_items())
        assert headers["X-signature"] == _sig(p.to_json(), secret)

    def test_no_signature_header_when_no_secret(self) -> None:
        s = WebhookSender()
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, timestamp=1.0)
        req = s._build_request(WebhookConfig(url="https://x.com"), p)
        headers = dict(req.header_items())
        assert "X-signature" not in headers

    def test_body_is_payload_json(self) -> None:
        s = WebhookSender()
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, timestamp=1.0)
        req = s._build_request(WebhookConfig(url="https://x.com"), p)
        assert req.data.decode("utf-8") == p.to_json()
        json.loads(req.data.decode("utf-8"))  # valid JSON

    def test_method_is_post(self) -> None:
        s = WebhookSender()
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, timestamp=1.0)
        req = s._build_request(WebhookConfig(url="https://x.com"), p)
        assert req.get_method() == "POST"

    def test_custom_headers_merged_with_signature(self) -> None:
        s = WebhookSender()
        secret = "k"
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, timestamp=1.0)
        req = s._build_request(
            WebhookConfig(
                url="https://x.com", secret=secret, headers={"X-Api": "v"}
            ),
            p,
        )
        headers = dict(req.header_items())
        assert headers["X-api"] == "v"
        assert headers["X-signature"] == _sig(p.to_json(), secret)


# ---------------------------------------------------------------------------
# send(): persistent pending / delivered stores
# ---------------------------------------------------------------------------
class TestSendPendingDelivered:
    @patch("urllib.request.urlopen")
    def test_success_moves_payload_to_delivered(self, mu: MagicMock) -> None:
        mu.return_value = _ok_response()
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://ok.com"))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        s.send(p)
        assert s.get_pending() == []
        assert s.get_delivered() == [p]

    @patch("urllib.request.urlopen")
    def test_failure_leaves_payload_in_pending(self, mu: MagicMock) -> None:
        mu.side_effect = URLError("refused")
        s = WebhookSender()
        s.add_endpoint(
            WebhookConfig(url="https://bad.com", retry_count=0, retry_delay=0.01)
        )
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        s.send(p)
        assert s.get_pending() == [p]
        assert s.get_delivered() == []

    @patch("urllib.request.urlopen")
    def test_two_endpoints_both_success_delivered_twice(self, mu: MagicMock) -> None:
        mu.return_value = _ok_response()
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        s.add_endpoint(WebhookConfig(url="https://b.com"))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        s.send(p)
        assert s.get_pending() == []
        assert s.get_delivered() == [p, p]

    @patch("urllib.request.urlopen")
    def test_non_matching_event_records_nothing(self, mu: MagicMock) -> None:
        mu.return_value = _ok_response()
        s = WebhookSender()
        s.add_endpoint(
            WebhookConfig(url="https://a.com", events=[WebhookEvent.ERROR_OCCURRED])
        )
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        s.send(p)
        assert s.get_pending() == []
        assert s.get_delivered() == []
        mu.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_mixed_success_and_failure(self, mu: MagicMock) -> None:
        # First endpoint succeeds, second fails -> delivered once, pending once.
        mu.side_effect = [_ok_response(), URLError("down")]
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        s.add_endpoint(
            WebhookConfig(url="https://b.com", retry_count=0, retry_delay=0.01)
        )
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        s.send(p)
        assert s.get_delivered() == [p]
        assert s.get_pending() == [p]


# ---------------------------------------------------------------------------
# get_stats / endpoint_count
# ---------------------------------------------------------------------------
class TestGetStats:
    def test_empty_sender_stats(self) -> None:
        s = WebhookSender()
        assert s.get_stats() == {
            "total_endpoints": 0,
            "enabled_endpoints": 0,
            "pending_payloads": 0,
            "delivered_payloads": 0,
        }

    def test_stats_counts_enabled_and_disabled(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com", enabled=True))
        s.add_endpoint(WebhookConfig(url="https://b.com", enabled=False))
        s.add_endpoint(WebhookConfig(url="https://c.com", enabled=True))
        st = s.get_stats()
        assert st["total_endpoints"] == 3
        assert st["enabled_endpoints"] == 2
        assert st["pending_payloads"] == 0
        assert st["delivered_payloads"] == 0
        assert s.endpoint_count == 3

    @patch("urllib.request.urlopen")
    def test_stats_reflect_pending_and_delivered(self, mu: MagicMock) -> None:
        mu.side_effect = [_ok_response(), URLError("down")]
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        s.add_endpoint(
            WebhookConfig(url="https://b.com", retry_count=0, retry_delay=0.01)
        )
        s.send(WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE))
        st = s.get_stats()
        assert st["pending_payloads"] == 1
        assert st["delivered_payloads"] == 1


# ---------------------------------------------------------------------------
# idempotence / property
# ---------------------------------------------------------------------------
class TestIdempotence:
    @patch("urllib.request.urlopen")
    def test_send_same_payload_twice_doubles_delivered(self, mu: MagicMock) -> None:
        mu.return_value = _ok_response()
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        s.send(p)
        s.send(p)
        assert s.get_delivered() == [p, p]
        assert s.get_pending() == []

    def test_get_pending_returns_live_list(self) -> None:
        s = WebhookSender()
        s.pending.append(WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE))
        assert len(s.get_pending()) == 1
        # get_pending returns the store itself (documented: "the list of
        # payloads still pending"); mutating it mutates the store.
        s.get_pending().clear()
        assert s.get_pending() == []


# ---------------------------------------------------------------------------
# end-to-end installed CLI run
# ---------------------------------------------------------------------------
class TestE2ECLI:
    def test_cli_help_exits_zero(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "usage" in (r.stdout + r.stderr).lower()
