"""Tests for URL history tracking."""

from __future__ import annotations

from personal_index.url_history import URLHistory, URLVisit


class TestURLVisit:
    """Tests for URLVisit dataclass."""

    def test_create_visit(self):
        v = URLVisit(url="http://example.com", status_code=200)
        assert v.url == "http://example.com"
        assert v.status_code == 200
        assert v.timestamp

    def test_to_dict(self):
        v = URLVisit(url="http://example.com", status_code=200, title="Test")
        d = v.to_dict()
        assert d["url"] == "http://example.com"
        assert d["title"] == "Test"

    def test_from_dict(self):
        data = {
            "url": "http://example.com",
            "timestamp": "2024-01-01T00:00:00",
            "status_code": 200,
            "content_length": 1000,
            "title": "Test",
            "user_agent": "bot",
            "response_time_ms": 50.0,
            "error": "",
        }
        v = URLVisit.from_dict(data)
        assert v.url == "http://example.com"
        assert v.response_time_ms == 50.0

    def test_from_dict_partial_dict_fills_defaults(self):
        """Pin the corrected docstring: from_dict unpacks data as keyword
        arguments (cls(**data)), so keys present map to fields and keys absent
        fall back to the dataclass defaults."""
        data = {
            "url": "http://partial.example.com",
            "status_code": 204,
            "response_time_ms": 12.5,
        }
        v = URLVisit.from_dict(data)
        # Keys present in data map to the exact field values.
        assert v.url == "http://partial.example.com"
        assert v.status_code == 204
        assert v.response_time_ms == 12.5
        # Sibling keys absent from data fall back to their dataclass defaults
        # (witnessing the doc-only fix against the returned object).
        assert v.title == ""
        assert v.content_length == 0
        assert v.user_agent == ""
        assert v.error == ""

    def test_defaults(self):
        v = URLVisit(url="http://example.com")
        assert v.status_code == 0
        assert v.content_length == 0
        assert v.error == ""


class TestURLHistory:
    """Tests for URLHistory class."""

    def test_record_visit(self):
        history = URLHistory()
        visit = history.record("http://example.com", status_code=200)
        assert visit.url == "http://example.com"
        assert len(history.get_visits()) == 1

    def test_record_multiple_visits(self):
        history = URLHistory()
        history.record("http://example.com", status_code=200)
        history.record("http://example.org", status_code=200)
        assert len(history.get_visits()) == 2

    def test_get_visits_by_url(self):
        history = URLHistory()
        history.record("http://example.com", status_code=200)
        history.record("http://example.org", status_code=200)
        visits = history.get_visits(url="http://example.com")
        assert len(visits) == 1
        assert visits[0].url == "http://example.com"

    def test_get_visits_limit(self):
        history = URLHistory()
        for i in range(10):
            history.record(f"http://example{i}.com")
        visits = history.get_visits(limit=3)
        assert len(visits) == 3

    def test_get_unique_urls(self):
        history = URLHistory()
        history.record("http://example.com")
        history.record("http://example.com")
        history.record("http://example.org")
        urls = history.get_unique_urls()
        assert len(urls) == 2

    def test_get_stats_empty(self):
        history = URLHistory()
        stats = history.get_stats()
        assert stats["total_visits"] == 0
        assert stats["unique_urls"] == 0

    def test_get_stats(self):
        history = URLHistory()
        history.record("http://example.com", status_code=200, response_time_ms=50.0)
        history.record("http://example.org", status_code=404, response_time_ms=100.0)
        stats = history.get_stats()
        assert stats["total_visits"] == 2
        assert stats["unique_urls"] == 2
        assert stats["error_count"] == 1
        assert stats["success_count"] == 1

    def test_get_domain_stats(self):
        history = URLHistory()
        history.record("http://example.com/page1", status_code=200)
        history.record("http://example.com/page2", status_code=200)
        history.record("http://example.org/page1", status_code=500)
        stats = history.get_domain_stats()
        assert stats["example.com"]["visits"] == 2
        assert stats["example.org"]["errors"] == 1

    def test_clear(self):
        history = URLHistory()
        for i in range(10):
            history.record(f"http://example{i}.com")
        count = history.clear()
        assert count == 10
        assert len(history.get_visits()) == 0

    def test_save_and_load(self, tmp_path):
        history = URLHistory()
        history.record("http://example.com", status_code=200, title="Test")
        filepath = str(tmp_path / "history.json")
        history.save(filepath)

        new_history = URLHistory()
        count = new_history.load(filepath)
        assert count == 1
        assert new_history.get_visits()[0].url == "http://example.com"

    def test_load_nonexistent_file(self, tmp_path):
        history = URLHistory()
        count = history.load(str(tmp_path / "nonexistent.json"))
        assert count == 0

    def test_max_entries(self):
        history = URLHistory(max_entries=5)
        for i in range(10):
            history.record(f"http://example{i}.com")
        assert len(history.get_visits()) == 5

    def test_record_with_error(self):
        history = URLHistory()
        history.record("http://example.com", status_code=200, error="timeout")
        stats = history.get_stats()
        assert stats["error_count"] == 1


class TestURLHistoryNonListGuard:
    """Regression tests for non-list JSON in load()."""

    def test_load_null_returns_zero(self, tmp_path):
        filepath = tmp_path / "history.json"
        filepath.write_text("null")
        history = URLHistory()
        count = history.load(str(filepath))
        assert count == 0

    def test_load_number_returns_zero(self, tmp_path):
        filepath = tmp_path / "history.json"
        filepath.write_text("42")
        history = URLHistory()
        count = history.load(str(filepath))
        assert count == 0

    def test_load_dict_returns_zero(self, tmp_path):
        filepath = tmp_path / "history.json"
        filepath.write_text('{"url": "http://example.com"}')
        history = URLHistory()
        count = history.load(str(filepath))
        assert count == 0

    def test_load_valid_list_still_works(self, tmp_path):
        filepath = tmp_path / "history.json"
        filepath.write_text(
            '[{"url": "http://example.com", "timestamp": "2024-01-01T00:00:00Z",'
            ' "status_code": 200, "content_length": 0, "title": "",'
            ' "user_agent": "", "response_time_ms": 0.0, "error": ""}]'
        )
        history = URLHistory()
        count = history.load(str(filepath))
        assert count == 1
        assert history.get_visits()[0].url == "http://example.com"

    def test_load_valid_after_invalid_not_suppressed(self, tmp_path):
        filepath = tmp_path / "history.json"
        filepath.write_text("null")
        history = URLHistory()
        count = history.load(str(filepath))
        assert count == 0
        filepath.write_text(
            '[{"url": "http://good.com", "timestamp": "2024-01-01T00:00:00Z",'
            ' "status_code": 200, "content_length": 0, "title": "",'
            ' "user_agent": "", "response_time_ms": 0.0, "error": ""}]'
        )
        count = history.load(str(filepath))
        assert count == 1
        assert history.get_visits()[0].url == "http://good.com"


class TestURLHistoryCorruptJSONGuard:
    """Regression: corrupt/truncated JSON in load() must not raise (TICKET-293)."""

    def test_load_corrupt_json_returns_zero(self, tmp_path):
        filepath = tmp_path / "history.json"
        filepath.write_text("{")
        history = URLHistory()
        count = history.load(str(filepath))
        assert count == 0

    def test_load_truncated_json_returns_zero(self, tmp_path):
        filepath = tmp_path / "history.json"
        filepath.write_text('[{"url": "http://example.com"')
        history = URLHistory()
        count = history.load(str(filepath))
        assert count == 0


class TestURLVisitToDict:
    """Pinning tests for URLVisit.to_dict (TICKET-511)."""

    def _make(self):
        return URLVisit(
            url="http://x.com",
            status_code=200,
            content_length=1000,
            title="T",
            user_agent="bot",
            response_time_ms=50.5,
            error="err",
        )

    def test_returns_dict_type(self):
        d = self._make().to_dict()
        assert isinstance(d, dict)

    def test_exact_key_set_and_order(self):
        d = self._make().to_dict()
        assert list(d.keys()) == [
            "url",
            "timestamp",
            "status_code",
            "content_length",
            "title",
            "user_agent",
            "response_time_ms",
            "error",
        ]

    def test_values_match_fields(self):
        v = self._make()
        d = v.to_dict()
        assert d["url"] == "http://x.com"
        assert d["status_code"] == 200
        assert d["content_length"] == 1000
        assert d["title"] == "T"
        assert d["user_agent"] == "bot"
        assert d["response_time_ms"] == 50.5
        assert d["error"] == "err"
        assert d["timestamp"] == v.timestamp

    def test_fresh_object_each_call(self):
        v = self._make()
        assert v.to_dict() is not v.to_dict()

    def test_round_trips_with_from_dict(self):
        v = self._make()
        assert URLVisit.from_dict(v.to_dict()) == v

    def test_does_not_mutate_self(self):
        v = self._make()
        before = (v.url, v.status_code, v.content_length, v.title,
                  v.user_agent, v.response_time_ms, v.error, v.timestamp)
        d = v.to_dict()
        d["url"] = "mutated"
        after = (v.url, v.status_code, v.content_length, v.title,
                 v.user_agent, v.response_time_ms, v.error, v.timestamp)
        assert before == after
