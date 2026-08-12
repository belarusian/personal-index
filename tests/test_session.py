"""Tests for crawl session tracking."""

import time

import pytest

from personal_index.session import (
    CrawlSession,
    SessionManager,
    SessionStats,
    SessionStatus,
)


class TestSessionStats:
    def test_default_values(self):
        stats = SessionStats()
        assert stats.urls_crawled == 0
        assert stats.success_rate == 0.0
        assert stats.total_processed == 0

    def test_success_rate(self):
        stats = SessionStats(urls_crawled=8, urls_failed=2)
        assert stats.success_rate == 0.8

    def test_total_processed(self):
        stats = SessionStats(urls_crawled=5, urls_failed=2, urls_skipped=3)
        assert stats.total_processed == 10

    def test_to_dict(self):
        stats = SessionStats(urls_crawled=10, urls_failed=1)
        d = stats.to_dict()
        assert d["urls_crawled"] == 10
        assert d["success_rate"] == pytest.approx(0.909, rel=0.01)


class TestCrawlSession:
    def test_creation(self):
        session = CrawlSession(session_id="s1", name="Test Crawl")
        assert session.status == SessionStatus.ACTIVE
        assert session.name == "Test Crawl"

    def test_pause_resume(self):
        session = CrawlSession(session_id="s1")
        session.pause()
        assert session.status == SessionStatus.PAUSED
        session.resume()
        assert session.status == SessionStatus.ACTIVE

    def test_complete(self):
        session = CrawlSession(session_id="s1")
        session.complete()
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None

    def test_fail(self):
        session = CrawlSession(session_id="s1")
        session.fail("Connection error")
        assert session.status == SessionStatus.FAILED
        assert "Connection error" in session.stats.errors

    def test_stop(self):
        session = CrawlSession(session_id="s1")
        session.stop()
        assert session.status == SessionStatus.STOPPED

    def test_record_url_crawled(self):
        session = CrawlSession(session_id="s1")
        session.record_url_crawled("http://example.com/page", size=1024)
        assert session.stats.urls_crawled == 1
        assert session.stats.bytes_downloaded == 1024
        assert "example.com" in session.stats.domains_seen

    def test_record_url_failed(self):
        session = CrawlSession(session_id="s1")
        session.record_url_failed("http://example.com", "timeout")
        assert session.stats.urls_failed == 1

    def test_record_url_skipped(self):
        session = CrawlSession(session_id="s1")
        session.record_url_skipped("http://example.com")
        assert session.stats.urls_skipped == 1

    def test_record_page_indexed(self):
        session = CrawlSession(session_id="s1")
        session.record_page_indexed()
        session.record_page_indexed()
        assert session.stats.pages_indexed == 2

    def test_duration(self):
        session = CrawlSession(session_id="s1")
        session.started_at = time.time() - 60
        assert session.duration >= 59

    def test_to_dict(self):
        session = CrawlSession(session_id="s1", name="Test")
        d = session.to_dict()
        assert d["session_id"] == "s1"
        assert d["name"] == "Test"
        assert "stats" in d


class TestSessionManager:
    def test_create_session(self):
        mgr = SessionManager()
        session = mgr.create_session("s1", "Test")
        assert mgr.session_count == 1
        assert session.session_id == "s1"

    def test_get_session(self):
        mgr = SessionManager()
        mgr.create_session("s1")
        session = mgr.get_session("s1")
        assert session is not None

    def test_get_missing_session(self):
        mgr = SessionManager()
        assert mgr.get_session("missing") is None

    def test_active_session(self):
        mgr = SessionManager()
        mgr.create_session("s1")
        active = mgr.get_active_session()
        assert active is not None
        assert active.session_id == "s1"

    def test_set_active(self):
        mgr = SessionManager()
        mgr.create_session("s1")
        mgr.create_session("s2")
        assert mgr.set_active("s2") is True
        active = mgr.get_active_session()
        assert active.session_id == "s2"

    def test_list_sessions(self):
        mgr = SessionManager()
        mgr.create_session("s1")
        mgr.create_session("s2")
        assert len(mgr.list_sessions()) == 2

    def test_list_active(self):
        mgr = SessionManager()
        mgr.create_session("s1")
        s2 = mgr.create_session("s2")
        s2.complete()
        assert len(mgr.list_active()) == 1

    def test_remove_session(self):
        mgr = SessionManager()
        mgr.create_session("s1")
        assert mgr.remove_session("s1") is True
        assert mgr.session_count == 0

    def test_save_and_load_session(self, tmp_path):
        mgr = SessionManager(storage_path=str(tmp_path))
        session = mgr.create_session("s1", "Test")
        session.record_url_crawled("http://example.com")
        mgr.save_session("s1")

        mgr2 = SessionManager()
        loaded = mgr2.load_session(str(tmp_path / "s1.json"))
        assert loaded is not None
        assert loaded.session_id == "s1"
        assert loaded.stats.urls_crawled == 1

    def test_load_missing_file(self):
        mgr = SessionManager()
        assert mgr.load_session("/nonexistent/file.json") is None
