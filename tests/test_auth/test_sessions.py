"""Tests for session management."""

from __future__ import annotations

import time

import pytest

from personal_index.auth.sessions import Session, SessionStore


@pytest.fixture
def store():
    return SessionStore(default_ttl=3600, cleanup_interval=999999)


class TestSession:
    def test_create_session(self):
        session = Session(user_id="user1")
        assert session.user_id == "user1"
        assert session.is_active is True
        assert session.data == {}

    def test_session_to_dict(self):
        session = Session(user_id="user1", data={"key": "value"})
        data = session.to_dict()
        assert data["user_id"] == "user1"
        assert data["data"] == {"key": "value"}

    def test_session_not_expired(self):
        session = Session(user_id="user1", expires_at=time.time() + 3600)
        assert session.is_expired() is False

    def test_session_expired(self):
        session = Session(user_id="user1", expires_at=time.time() - 1)
        assert session.is_expired() is True

    def test_session_inactive(self):
        session = Session(user_id="user1", is_active=False)
        assert session.is_expired() is True


class TestSessionStore:
    def test_create_session(self, store):
        session = store.create_session("user1")
        assert session.user_id == "user1"
        assert session.session_id is not None

    def test_create_session_with_data(self, store):
        session = store.create_session(
            "user1", data={"role": "admin"}, ip_address="127.0.0.1"
        )
        assert session.data == {"role": "admin"}
        assert session.ip_address == "127.0.0.1"

    def test_create_session_with_ttl(self, store):
        session = store.create_session("user1", ttl=7200)
        assert session.expires_at is not None
        assert session.expires_at > time.time() + 7000

    def test_get_valid_session(self, store):
        session = store.create_session("user1")
        retrieved = store.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.user_id == "user1"

    def test_get_nonexistent_session(self, store):
        assert store.get_session("nonexistent") is None

    def test_get_expired_session(self):
        store = SessionStore(default_ttl=0)
        session = store.create_session("user1")
        time.sleep(0.01)
        assert store.get_session(session.session_id) is None

    def test_update_session(self, store):
        session = store.create_session("user1")
        assert store.update_session(session.session_id, data={"key": "value"}) is True
        retrieved = store.get_session(session.session_id)
        assert retrieved.data["key"] == "value"

    def test_update_nonexistent_session(self, store):
        assert store.update_session("nonexistent") is False

    def test_update_session_extend_ttl(self, store):
        session = store.create_session("user1", ttl=60)
        old_expiry = session.expires_at
        store.update_session(session.session_id, extend_ttl=3600)
        retrieved = store.get_session(session.session_id)
        assert retrieved.expires_at > old_expiry

    def test_destroy_session(self, store):
        session = store.create_session("user1")
        assert store.destroy_session(session.session_id) is True
        assert store.get_session(session.session_id) is None

    def test_destroy_nonexistent_session(self, store):
        assert store.destroy_session("nonexistent") is False

    def test_destroy_user_sessions(self, store):
        store.create_session("user1")
        store.create_session("user1")
        store.create_session("user2")
        assert store.destroy_user_sessions("user1") == 2
        assert store.get_active_count("user1") == 0
        assert store.get_active_count("user2") == 1

    def test_get_active_count(self, store):
        store.create_session("user1")
        store.create_session("user1")
        store.create_session("user2")
        assert store.get_active_count() == 3
        assert store.get_active_count("user1") == 2

    def test_cleanup_expired(self):
        store = SessionStore(default_ttl=0)
        store.create_session("user1")
        store.create_session("user2")
        time.sleep(0.01)
        removed = store.cleanup_expired()
        assert removed == 2
        assert store.get_active_count() == 0

    def test_last_accessed_updated(self, store):
        session = store.create_session("user1")
        old_accessed = session.last_accessed
        time.sleep(0.01)
        store.get_session(session.session_id)
        retrieved = store.get_session(session.session_id)
        assert retrieved.last_accessed > old_accessed
