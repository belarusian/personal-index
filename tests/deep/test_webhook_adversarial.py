"""Adversarial deep tests for personal_index.webhook (cycle 254).

Covers: WebhookPayload.to_dict/to_json round-trips, WebhookConfig.should_send
guard inputs, WebhookSender add/remove/send with adversarial inputs,
_validate_url_scheme edge cases, and one end-to-end CLI run.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

from personal_index.webhook import (
    WebhookConfig,
    WebhookEvent,
    WebhookPayload,
    WebhookSender,
)


# ---------------------------------------------------------------------------
# WebhookPayload.to_dict
# ---------------------------------------------------------------------------

class TestPayloadToDict:
    def test_exactly_four_keys(self) -> None:
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, data={"a": 1})
        d = p.to_dict()
        assert set(d.keys()) == {"event", "data", "timestamp", "source"}

    def test_event_is_value_string_not_enum(self) -> None:
        p = WebhookPayload(event=WebhookEvent.INDEX_UPDATE)
        d = p.to_dict()
        assert d["event"] == "index_update"
        assert isinstance(d["event"], str)
        assert not isinstance(d["event"], WebhookEvent)

    def test_data_round_trip(self) -> None:
        data = {"nested": {"key": [1, 2, 3]}, "unicode": "héllo wörld"}
        p = WebhookPayload(event=WebhookEvent.ERROR_OCCURRED, data=data)
        d = p.to_dict()
        assert d["data"] == data

    def test_empty_data(self) -> None:
        p = WebhookPayload(event=WebhookEvent.HEALTH_CHECK)
        d = p.to_dict()
        assert d["data"] == {}

    def test_none_in_data(self) -> None:
        p = WebhookPayload(event=WebhookEvent.CRAWL_FAILED, data={"val": None})
        d = p.to_dict()
        assert d["data"]["val"] is None

    def test_timestamp_is_float(self) -> None:
        p = WebhookPayload(event=WebhookEvent.BACKUP_COMPLETE)
        d = p.to_dict()
        assert isinstance(d["timestamp"], float)

    def test_source_default(self) -> None:
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        d = p.to_dict()
        assert d["source"] == "personal-index"

    def test_custom_source(self) -> None:
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, source="custom-src")
        d = p.to_dict()
        assert d["source"] == "custom-src"


# ---------------------------------------------------------------------------
# WebhookPayload.to_json
# ---------------------------------------------------------------------------

class TestPayloadToJson:
    def test_round_trip(self) -> None:
        p = WebhookPayload(event=WebhookEvent.INDEX_UPDATE, data={"x": 42})
        j = p.to_json()
        parsed = json.loads(j)
        assert parsed["event"] == "index_update"
        assert parsed["data"] == {"x": 42}
        assert parsed["source"] == "personal-index"

    def test_unicode_round_trip(self) -> None:
        p = WebhookPayload(event=WebhookEvent.ERROR_OCCURRED, data={"msg": "café ☕"})
        j = p.to_json()
        parsed = json.loads(j)
        assert parsed["data"]["msg"] == "café ☕"

    def test_empty_data_json(self) -> None:
        p = WebhookPayload(event=WebhookEvent.HEALTH_CHECK)
        j = p.to_json()
        parsed = json.loads(j)
        assert parsed["data"] == {}

    def test_json_is_valid_string(self) -> None:
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        j = p.to_json()
        assert isinstance(j, str)
        json.loads(j)  # must not raise


# ---------------------------------------------------------------------------
# WebhookConfig.should_send
# ---------------------------------------------------------------------------

class TestConfigShouldSend:
    def test_disabled_returns_false(self) -> None:
        cfg = WebhookConfig(url="https://example.com/hook", enabled=False)
        assert cfg.should_send(WebhookEvent.CRAWL_COMPLETE) is False

    def test_disabled_ignores_events(self) -> None:
        cfg = WebhookConfig(
            url="https://example.com/hook",
            events=[WebhookEvent.CRAWL_COMPLETE],
            enabled=False,
        )
        assert cfg.should_send(WebhookEvent.CRAWL_COMPLETE) is False

    def test_enabled_empty_events_returns_true(self) -> None:
        cfg = WebhookConfig(url="https://example.com/hook", events=[])
        assert cfg.should_send(WebhookEvent.CRAWL_COMPLETE) is True
        assert cfg.should_send(WebhookEvent.ERROR_OCCURRED) is True

    def test_enabled_with_matching_event(self) -> None:
        cfg = WebhookConfig(
            url="https://example.com/hook",
            events=[WebhookEvent.INDEX_UPDATE],
        )
        assert cfg.should_send(WebhookEvent.INDEX_UPDATE) is True

    def test_enabled_with_non_matching_event(self) -> None:
        cfg = WebhookConfig(
            url="https://example.com/hook",
            events=[WebhookEvent.INDEX_UPDATE],
        )
        assert cfg.should_send(WebhookEvent.CRAWL_COMPLETE) is False

    def test_multiple_events(self) -> None:
        cfg = WebhookConfig(
            url="https://example.com/hook",
            events=[WebhookEvent.CRAWL_COMPLETE, WebhookEvent.CRAWL_FAILED],
        )
        assert cfg.should_send(WebhookEvent.CRAWL_COMPLETE) is True
        assert cfg.should_send(WebhookEvent.CRAWL_FAILED) is True
        assert cfg.should_send(WebhookEvent.INDEX_UPDATE) is False

    def test_duplicate_events_in_list(self) -> None:
        cfg = WebhookConfig(
            url="https://example.com/hook",
            events=[WebhookEvent.CRAWL_COMPLETE, WebhookEvent.CRAWL_COMPLETE],
        )
        assert cfg.should_send(WebhookEvent.CRAWL_COMPLETE) is True


# ---------------------------------------------------------------------------
# WebhookSender.add_endpoint / remove_endpoint / endpoint_count
# ---------------------------------------------------------------------------

class TestSenderEndpoints:
    def test_add_and_count(self) -> None:
        s = WebhookSender()
        assert s.endpoint_count == 0
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        s.add_endpoint(WebhookConfig(url="https://b.com"))
        assert s.endpoint_count == 2

    def test_duplicate_urls_allowed(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://same.com"))
        s.add_endpoint(WebhookConfig(url="https://same.com"))
        assert s.endpoint_count == 2

    def test_remove_existing(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        s.add_endpoint(WebhookConfig(url="https://b.com"))
        assert s.remove_endpoint("https://a.com") is True
        assert s.endpoint_count == 1

    def test_remove_nonexistent(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        assert s.remove_endpoint("https://nonexistent.com") is False
        assert s.endpoint_count == 1

    def test_remove_empty_string(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com"))
        assert s.remove_endpoint("") is False
        assert s.endpoint_count == 1

    def test_remove_first_of_duplicates(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://dup.com"))
        s.add_endpoint(WebhookConfig(url="https://dup.com"))
        assert s.remove_endpoint("https://dup.com") is True
        assert s.endpoint_count == 1
        # Second remove should still work
        assert s.remove_endpoint("https://dup.com") is True
        assert s.endpoint_count == 0

    def test_remove_all_then_empty(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://x.com"))
        s.remove_endpoint("https://x.com")
        assert s.endpoint_count == 0
        assert s.remove_endpoint("https://x.com") is False


# ---------------------------------------------------------------------------
# WebhookSender.send (mocked network)
# ---------------------------------------------------------------------------

class TestSenderSend:
    def test_no_endpoints_returns_empty(self) -> None:
        s = WebhookSender()
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert results == []

    def test_all_disabled_returns_empty(self) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://a.com", enabled=False))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert results == []

    def test_event_filter_skips_non_matching(self) -> None:
        s = WebhookSender()
        s.add_endpoint(
            WebhookConfig(
                url="https://a.com",
                events=[WebhookEvent.INDEX_UPDATE],
            )
        )
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert results == []

    @patch("urllib.request.urlopen")
    def test_successful_send(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="https://ok.com/hook"))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["status"] == 200
        assert results[0]["attempts"] == 1
        assert results[0]["url"] == "https://ok.com/hook"

    @patch("urllib.request.urlopen")
    def test_url_error_retries_then_fails(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = URLError("connection refused")

        s = WebhookSender()
        s.add_endpoint(
            WebhookConfig(
                url="https://fail.com/hook",
                retry_count=2,
                retry_delay=0.01,
            )
        )
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert results[0]["attempts"] == 3  # retry_count + 1
        assert "connection refused" in results[0]["error"]

    @patch("urllib.request.urlopen")
    def test_invalid_scheme_no_network(self, mock_urlopen: MagicMock) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="ftp://files.example.com/hook"))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Unsupported URL scheme" in results[0]["error"]
        assert results[0]["attempts"] == 0
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_empty_scheme_url(self, mock_urlopen: MagicMock) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url=""))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Unsupported URL scheme" in results[0]["error"]
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_whitespace_url(self, mock_urlopen: MagicMock) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="   "))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert len(results) == 1
        assert results[0]["success"] is False
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_file_scheme_rejected(self, mock_urlopen: MagicMock) -> None:
        s = WebhookSender()
        s.add_endpoint(WebhookConfig(url="file:///etc/passwd"))
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        results = s.send(p)
        assert results[0]["success"] is False
        assert "Unsupported URL scheme" in results[0]["error"]
        mock_urlopen.assert_not_called()


# ---------------------------------------------------------------------------
# _validate_url_scheme direct
# ---------------------------------------------------------------------------

class TestValidateUrlScheme:
    def test_http_valid(self) -> None:
        s = WebhookSender()
        assert s._validate_url_scheme("http://example.com") is None

    def test_https_valid(self) -> None:
        s = WebhookSender()
        assert s._validate_url_scheme("https://example.com") is None

    def test_ftp_invalid(self) -> None:
        s = WebhookSender()
        err = s._validate_url_scheme("ftp://example.com")
        assert err is not None
        assert "ftp" in err

    def test_empty_string(self) -> None:
        s = WebhookSender()
        err = s._validate_url_scheme("")
        assert err is not None

    def test_whitespace_only(self) -> None:
        s = WebhookSender()
        err = s._validate_url_scheme("   ")
        assert err is not None

    def test_no_scheme(self) -> None:
        s = WebhookSender()
        err = s._validate_url_scheme("example.com/path")
        assert err is not None


# ---------------------------------------------------------------------------
# _build_request
# ---------------------------------------------------------------------------

class TestBuildRequest:
    def test_content_type_header(self) -> None:
        s = WebhookSender()
        cfg = WebhookConfig(url="https://example.com/hook")
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, data={"k": "v"})
        req = s._build_request(cfg, p)
        assert req.get_header("Content-type") == "application/json"

    def test_custom_headers_merged(self) -> None:
        s = WebhookSender()
        cfg = WebhookConfig(
            url="https://example.com/hook",
            headers={"Authorization": "Bearer tok123"},
        )
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        req = s._build_request(cfg, p)
        assert req.get_header("Authorization") == "Bearer tok123"
        assert req.get_header("Content-type") == "application/json"

    def test_method_is_post(self) -> None:
        s = WebhookSender()
        cfg = WebhookConfig(url="https://example.com/hook")
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE)
        req = s._build_request(cfg, p)
        assert req.get_method() == "POST"

    def test_body_is_json(self) -> None:
        s = WebhookSender()
        cfg = WebhookConfig(url="https://example.com/hook")
        p = WebhookPayload(event=WebhookEvent.INDEX_UPDATE, data={"n": 5})
        req = s._build_request(cfg, p)
        body = req.data
        assert body is not None
        parsed = json.loads(body.decode("utf-8"))
        assert parsed["event"] == "index_update"
        assert parsed["data"] == {"n": 5}


# ---------------------------------------------------------------------------
# Idempotence / property checks
# ---------------------------------------------------------------------------

class TestIdempotence:
    def test_add_remove_add_idempotent(self) -> None:
        s = WebhookSender()
        cfg = WebhookConfig(url="https://idem.com")
        s.add_endpoint(cfg)
        s.remove_endpoint("https://idem.com")
        s.add_endpoint(cfg)
        assert s.endpoint_count == 1

    def test_to_dict_idempotent(self) -> None:
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, data={"x": 1})
        d1 = p.to_dict()
        d2 = p.to_dict()
        assert d1 == d2

    def test_to_json_idempotent(self) -> None:
        p = WebhookPayload(event=WebhookEvent.CRAWL_COMPLETE, data={"x": 1})
        j1 = p.to_json()
        j2 = p.to_json()
        assert j1 == j2


# ---------------------------------------------------------------------------
# End-to-end CLI run
# ---------------------------------------------------------------------------

class TestE2ECLI:
    def test_cli_help_exits_zero(self) -> None:
        """Run the installed CLI with --help; must exit 0."""
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Must print some usage text
        assert "usage" in (result.stdout + result.stderr).lower()
