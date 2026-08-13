"""Tests for session management."""

import time

from personal_index.auth.sessions import Session, SessionStore


class TestSession:
    def test_default(self):
        s = Session()
        assert s.is_active is True
        assert s.session_id != ""

    def test_to_dict(self):
        s = Session(user_id="u1")
        d = s.to_dict()
        assert d["user_id"] == "u1"
        assert "session_id" in d

    def test_not_expired(self):
        s = Session(expires_at=time.time() + 3600)
        assert s.is_expired() is False

    def test_expired(self):
        s = Session(expires_at=time.time() - 100)
        assert s.is_expired() is True

    def test_inactive_is_expired(self):
        s = Session(is_active=False, expires_at=time.time() + 3600)
        assert s.is_expired() is True


class TestSessionStore:
    def test_create_session(self):
        store = SessionStore()
        s = store.create_session("u1")
        assert s.user_id == "u1"

    def test_get_session(self):
        store = SessionStore()
        s = store.create_session("u1")
        got = store.get_session(s.session_id)
        assert got is not None

    def test_get_expired_session(self):
        store = SessionStore(default_ttl=1)
        s = store.create_session("u1")
        s.expires_at = time.time() - 1
        assert store.get_session(s.session_id) is None

    def test_update_session(self):
        store = SessionStore()
        s = store.create_session("u1")
        assert store.update_session(s.session_id, data={"key": "val"}) is True
        assert store.get_session(s.session_id).data["key"] == "val"

    def test_update_missing_session(self):
        store = SessionStore()
        assert store.update_session("missing") is False

    def test_destroy_session(self):
        store = SessionStore()
        s = store.create_session("u1")
        assert store.destroy_session(s.session_id) is True
        assert store.get_session(s.session_id) is None

    def test_destroy_missing(self):
        store = SessionStore()
        assert store.destroy_session("missing") is False

    def test_destroy_user_sessions(self):
        store = SessionStore()
        store.create_session("u1")
        store.create_session("u1")
        store.create_session("u2")
        removed = store.destroy_user_sessions("u1")
        assert removed == 2

    def test_active_count(self):
        store = SessionStore()
        store.create_session("u1")
        store.create_session("u2")
        assert store.get_active_count() == 2

    def test_active_count_by_user(self):
        store = SessionStore()
        store.create_session("u1")
        store.create_session("u1")
        store.create_session("u2")
        assert store.get_active_count(user_id="u1") == 2

    def test_cleanup_expired(self):
        store = SessionStore(default_ttl=1)
        s = store.create_session("u1")
        s.expires_at = time.time() - 1
        removed = store.cleanup_expired()
        assert removed == 1
