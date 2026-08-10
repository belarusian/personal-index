"""Tests for the webhook notification system."""

import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import URLError
from personal_index.webhook import (
    WebhookSender,
    WebhookConfig,
    WebhookPayload,
    WebhookEvent,
)


class TestWebhookEvent:
    def test_event_values(self):
        assert WebhookEvent.CRAWL_COMPLETE.value == "crawl_complete"
        assert WebhookEvent.ERROR_OCCURRED.value == "error_occurred"


class TestWebhookPayload:
    def test_to_dict(self):
        payload = WebhookPayload(
            event=WebhookEvent.CRAWL_COMPLETE,
            data={"url": "http://example.com"},
        )
        d = payload.to_dict()
        assert d["event"] == "crawl_complete"
        assert d["data"]["url"] == "http://example.com"
        assert d["source"] == "personal-index"

    def test_to_json(self):
        payload = WebhookPayload(event=WebhookEvent.INDEX_UPDATE, data={"count": 42})
        j = payload.to_json()
        parsed = json.loads(j)
        assert parsed["event"] == "index_update"
        assert parsed["data"]["count"] == 42


class TestWebhookConfig:
    def test_should_send_all_events(self):
        config = WebhookConfig(url="http://hook.example.com")
        assert config.should_send(WebhookEvent.CRAWL_COMPLETE) is True

    def test_should_send_specific_events(self):
        config = WebhookConfig(
            url="http://hook.example.com",
            events=[WebhookEvent.CRAWL_COMPLETE],
        )
        assert config.should_send(WebhookEvent.CRAWL_COMPLETE) is True
        assert config.should_send(WebhookEvent.ERROR_OCCURRED) is False

    def test_disabled_config(self):
        config = WebhookConfig(url="http://hook.example.com", enabled=False)
        assert config.should_send(WebhookEvent.CRAWL_COMPLETE) is False

    def test_custom_headers(self):
        config = WebhookConfig(
            url="http://hook.example.com",
            headers={"Authorization": "Bearer token123"},
        )
        assert config.headers["Authorization"] == "Bearer token123"


class TestWebhookSender:
    def test_add_endpoint(self):
        sender = WebhookSender()
        config = WebhookConfig(url="http://hook.example.com")
        sender.add_endpoint(config)
        assert sender.endpoint_count == 1

    def test_remove_endpoint(self):
        sender = WebhookSender()
        config = WebhookConfig(url="http://hook.example.com")
        sender.add_endpoint(config)
        assert sender.remove_endpoint("http://hook.example.com") is True
        assert sender.endpoint_count == 0

    def test_remove_missing_endpoint(self):
        sender = WebhookSender()
        assert sender.remove_endpoint("http://missing.com") is False

    def test_send_to_matching_endpoint(self):
        sender = WebhookSender()
        config = WebhookConfig(url="http://hook.example.com")
        sender.add_endpoint(config)

        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            results = sender.send(payload)
            assert len(results) == 1
            assert results[0]["success"] is True

    def test_send_skips_non_matching_events(self):
        sender = WebhookSender()
        config = WebhookConfig(
            url="http://hook.example.com",
            events=[WebhookEvent.CRAWL_COMPLETE],
        )
        sender.add_endpoint(config)
        payload = WebhookPayload(event=WebhookEvent.ERROR_OCCURRED)

        with patch("urllib.request.urlopen") as mock_urlopen:
            results = sender.send(payload)
            assert len(results) == 0
            mock_urlopen.assert_not_called()

    def test_send_retry_on_failure(self):
        sender = WebhookSender()
        config = WebhookConfig(
            url="http://hook.example.com",
            retry_count=2,
            retry_delay=0.01,
        )
        sender.add_endpoint(config)
        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen", side_effect=URLError("fail")):
            with patch("personal_index.webhook.time.sleep"):
                results = sender.send(payload)
                assert len(results) == 1
                assert results[0]["success"] is False
                assert results[0]["attempts"] == 3

    def test_send_disabled_endpoint(self):
        sender = WebhookSender()
        config = WebhookConfig(url="http://hook.example.com", enabled=False)
        sender.add_endpoint(config)
        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen") as mock_urlopen:
            results = sender.send(payload)
            assert len(results) == 0
            mock_urlopen.assert_not_called()

    def test_multiple_endpoints(self):
        sender = WebhookSender()
        sender.add_endpoint(WebhookConfig(url="http://hook1.com"))
        sender.add_endpoint(WebhookConfig(url="http://hook2.com"))
        assert sender.endpoint_count == 2

        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            results = sender.send(payload)
            assert len(results) == 2


class TestWebhookSenderExceptionHandling:
    """Tests for TICKET-45: narrow exception handling in webhook sender."""

    def test_catches_urLError(self):
        """WebhookSender catches URLError and retries."""
        sender = WebhookSender()
        config = WebhookConfig(
            url="http://hook.example.com",
            retry_count=1,
            retry_delay=0.01,
        )
        sender.add_endpoint(config)
        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen", side_effect=URLError("dns fail")):
            with patch("personal_index.webhook.time.sleep"):
                results = sender.send(payload)
                assert len(results) == 1
                assert results[0]["success"] is False
                assert results[0]["attempts"] == 2

    def test_catches_oserror(self):
        """WebhookSender catches OSError and retries."""
        sender = WebhookSender()
        config = WebhookConfig(
            url="http://hook.example.com",
            retry_count=1,
            retry_delay=0.01,
        )
        sender.add_endpoint(config)
        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen", side_effect=OSError("connection reset")):
            with patch("personal_index.webhook.time.sleep"):
                results = sender.send(payload)
                assert len(results) == 1
                assert results[0]["success"] is False
                assert results[0]["attempts"] == 2

    def test_catches_timeout_error(self):
        """WebhookSender catches TimeoutError and retries."""
        sender = WebhookSender()
        config = WebhookConfig(
            url="http://hook.example.com",
            retry_count=1,
            retry_delay=0.01,
        )
        sender.add_endpoint(config)
        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with patch("personal_index.webhook.time.sleep"):
                results = sender.send(payload)
                assert len(results) == 1
                assert results[0]["success"] is False
                assert results[0]["attempts"] == 2

    def test_does_not_catch_generic_exception(self):
        """WebhookSender does NOT catch generic Exception (TICKET-45 fix)."""
        sender = WebhookSender()
        config = WebhookConfig(
            url="http://hook.example.com",
            retry_count=1,
            retry_delay=0.01,
        )
        sender.add_endpoint(config)
        payload = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)

        with patch("urllib.request.urlopen", side_effect=ValueError("unexpected")):
            with pytest.raises(ValueError, match="unexpected"):
                sender.send(payload)
