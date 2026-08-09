"""Tests for content_api_keys module - manage API keys for external services."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from personal_index.content_api_keys import (
    APIKeyEntry,
    APIKeyStore,
    APIKeyScope,
    APIKeyStatus,
    APIKeyUsage,
)


class TestAPIKeyScope:
    """Tests for APIKeyScope enum."""

    def test_scope_values(self):
        assert APIKeyScope.READ.value == "read"
        assert APIKeyScope.WRITE.value == "write"
        assert APIKeyScope.ADMIN.value == "admin"
        assert APIKeyScope.CRAWL.value == "crawl"
        assert APIKeyScope.INDEX.value == "index"


class TestAPIKeyStatus:
    """Tests for APIKeyStatus enum."""

    def test_status_values(self):
        assert APIKeyStatus.ACTIVE.value == "active"
        assert APIKeyStatus.REVOKED.value == "revoked"
        assert APIKeyStatus.EXPIRED.value == "expired"
        assert APIKeyStatus.SUSPENDED.value == "suspended"


class TestAPIKeyEntry:
    """Tests for APIKeyEntry model."""

    def test_create_key(self):
        key = APIKeyEntry(name="test-key", owner="user1")
        assert key.name == "test-key"
        assert key.owner == "user1"
        assert key.status == APIKeyStatus.ACTIVE
        assert len(key.key_id) == 16
        assert key.scopes == [APIKeyScope.READ]

    def test_key_with_custom_scopes(self):
        key = APIKeyEntry(
            name="admin-key",
            owner="admin",
            scopes=[APIKeyScope.ADMIN, APIKeyScope.CRAWL],
        )
        assert APIKeyScope.ADMIN in key.scopes
        assert APIKeyScope.CRAWL in key.scopes

    def test_key_with_expiry(self):
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        key = APIKeyEntry(name="temp-key", owner="user1", expires_at=expires)
        assert key.expires_at == expires
        assert key.is_expired() is False

    def test_key_is_expired(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        key = APIKeyEntry(name="old-key", owner="user1", expires_at=past)
        assert key.is_expired() is True

    def test_key_is_valid(self):
        key = APIKeyEntry(name="active-key", owner="user1")
        assert key.is_valid() is True

    def test_key_is_valid_revoked(self):
        key = APIKeyEntry(name="revoked-key", owner="user1")
        key.revoke()
        assert key.is_valid() is False

    def test_key_is_valid_expired(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        key = APIKeyEntry(name="expired-key", owner="user1", expires_at=past)
        assert key.is_valid() is False

    def test_key_revoke(self):
        key = APIKeyEntry(name="test-key", owner="user1")
        key.revoke()
        assert key.status == APIKeyStatus.REVOKED

    def test_key_suspend(self):
        key = APIKeyEntry(name="test-key", owner="user1")
        key.suspend()
        assert key.status == APIKeyStatus.SUSPENDED

    def test_key_activate(self):
        key = APIKeyEntry(name="test-key", owner="user1")
        key.revoke()
        key.activate()
        assert key.status == APIKeyStatus.ACTIVE

    def test_key_to_dict(self):
        key = APIKeyEntry(name="test-key", owner="user1")
        d = key.to_dict()
        assert d["name"] == "test-key"
        assert d["owner"] == "user1"
        assert d["status"] == APIKeyStatus.ACTIVE

    def test_key_has_scope(self):
        key = APIKeyEntry(
            name="test-key",
            owner="user1",
            scopes=[APIKeyScope.READ, APIKeyScope.CRAWL],
        )
        assert key.has_scope(APIKeyScope.READ) is True
        assert key.has_scope(APIKeyScope.WRITE) is False


class TestAPIKeyUsage:
    """Tests for APIKeyUsage model."""

    def test_create_usage(self):
        usage = APIKeyUsage(key_id="abc123", endpoint="/api/search")
        assert usage.key_id == "abc123"
        assert usage.endpoint == "/api/search"
        assert usage.timestamp is not None

    def test_usage_to_dict(self):
        usage = APIKeyUsage(key_id="abc123", endpoint="/api/search")
        d = usage.to_dict()
        assert d["key_id"] == "abc123"
        assert d["endpoint"] == "/api/search"


class TestAPIKeyStore:
    """Tests for APIKeyStore class."""

    def test_create_key(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        assert key.name == "test-key"
        assert key.owner == "user1"

    def test_get_key(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        retrieved = store.get_key(key.key_id)
        assert retrieved is not None
        assert retrieved.name == "test-key"

    def test_get_key_not_found(self):
        store = APIKeyStore()
        assert store.get_key("nonexistent") is None

    def test_list_keys(self):
        store = APIKeyStore()
        store.create_key(name="key1", owner="user1")
        store.create_key(name="key2", owner="user2")
        keys = store.list_keys()
        assert len(keys) == 2

    def test_list_keys_by_owner(self):
        store = APIKeyStore()
        store.create_key(name="key1", owner="user1")
        store.create_key(name="key2", owner="user2")
        keys = store.list_keys(owner="user1")
        assert len(keys) == 1
        assert keys[0].name == "key1"

    def test_revoke_key(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        store.revoke_key(key.key_id)
        assert store.get_key(key.key_id).status == APIKeyStatus.REVOKED

    def test_delete_key(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        store.delete_key(key.key_id)
        assert store.get_key(key.key_id) is None

    def test_validate_key(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        result = store.validate_key(key.key_id, APIKeyScope.READ)
        assert result.is_valid is True

    def test_validate_key_no_scope(self):
        store = APIKeyStore()
        key = store.create_key(
            name="read-only-key",
            owner="user1",
            scopes=[APIKeyScope.READ],
        )
        result = store.validate_key(key.key_id, APIKeyScope.WRITE)
        assert result.is_valid is False

    def test_validate_key_revoked(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        store.revoke_key(key.key_id)
        result = store.validate_key(key.key_id, APIKeyScope.READ)
        assert result.is_valid is False

    def test_record_usage(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        store.record_usage(key.key_id, "/api/search")
        assert len(key.usage_history) == 1

    def test_get_usage_history(self):
        store = APIKeyStore()
        key = store.create_key(name="test-key", owner="user1")
        store.record_usage(key.key_id, "/api/search")
        store.record_usage(key.key_id, "/api/crawl")
        history = store.get_usage_history(key.key_id)
        assert len(history) == 2

    def test_key_count(self):
        store = APIKeyStore()
        store.create_key(name="key1", owner="user1")
        store.create_key(name="key2", owner="user1")
        assert store.key_count == 2

    def test_active_key_count(self):
        store = APIKeyStore()
        store.create_key(name="key1", owner="user1")
        key2 = store.create_key(name="key2", owner="user1")
        store.revoke_key(key2.key_id)
        assert store.active_key_count == 1
