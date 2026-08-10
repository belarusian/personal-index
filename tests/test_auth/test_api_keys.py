"""Tests for API key management."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from personal_index.auth.api_keys import (
    APIKey,
    APIKeyStore,
    validate_api_key,
)


@pytest.fixture
def store():
    return APIKeyStore()


class TestAPIKey:
    def test_create_api_key(self):
        key = APIKey(name="test-key", owner="user1")
        assert key.name == "test-key"
        assert key.owner == "user1"
        assert key.is_active is True
        assert key.usage_count == 0

    def test_api_key_to_dict(self):
        key = APIKey(name="test-key", owner="user1", permissions=["read"])
        data = key.to_dict()
        assert data["name"] == "test-key"
        assert data["permissions"] == ["read"]
        assert "hashed_key" not in data


class TestAPIKeyStore:
    def test_create_key(self, store):
        raw_key, metadata = store.create_key("user1", name="my-key")
        assert raw_key.startswith("pk_")
        assert metadata.name == "my-key"
        assert metadata.owner == "user1"
        assert metadata.key_id is not None

    def test_create_key_with_permissions(self, store):
        _raw_key, metadata = store.create_key(
            "user1", permissions=["read:index", "write:index"]
        )
        assert metadata.permissions == ["read:index", "write:index"]

    def test_create_key_with_expiry(self, store):
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        _raw_key, metadata = store.create_key("user1", expires_at=expires)
        assert metadata.expires_at == expires

    def test_create_key_custom_prefix(self, store):
        raw_key, _metadata = store.create_key("user1", prefix="sk_")
        assert raw_key.startswith("sk_")

    def test_validate_valid_key(self, store):
        raw_key, _ = store.create_key("user1", name="test")
        result = store.validate_key(raw_key)
        assert result is not None
        assert result.owner == "user1"
        assert result.usage_count == 1

    def test_validate_invalid_key(self, store):
        result = store.validate_key("pk_nonexistent")
        assert result is None

    def test_validate_revoked_key(self, store):
        raw_key, metadata = store.create_key("user1")
        store.revoke_key(metadata.key_id)
        result = store.validate_key(raw_key)
        assert result is None

    def test_validate_expired_key(self, store):
        expires = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        raw_key, _ = store.create_key("user1", expires_at=expires)
        result = store.validate_key(raw_key)
        assert result is None

    def test_usage_count_increments(self, store):
        raw_key, _ = store.create_key("user1")
        store.validate_key(raw_key)
        store.validate_key(raw_key)
        store.validate_key(raw_key)
        result = store.validate_key(raw_key)
        assert result.usage_count == 4

    def test_last_used_at_updated(self, store):
        raw_key, _ = store.create_key("user1")
        result = store.validate_key(raw_key)
        assert result.last_used_at is not None

    def test_revoke_key(self, store):
        _, metadata = store.create_key("user1")
        assert store.revoke_key(metadata.key_id) is True
        key = store.get_key(metadata.key_id)
        assert key.is_active is False

    def test_revoke_nonexistent_key(self, store):
        assert store.revoke_key("nonexistent") is False

    def test_get_key(self, store):
        _, metadata = store.create_key("user1")
        key = store.get_key(metadata.key_id)
        assert key is not None
        assert key.key_id == metadata.key_id

    def test_get_nonexistent_key(self, store):
        assert store.get_key("nonexistent") is None

    def test_list_keys(self, store):
        store.create_key("user1", name="key1")
        store.create_key("user1", name="key2")
        store.create_key("user2", name="key3")
        assert len(store.list_keys("user1")) == 2
        assert len(store.list_keys("user2")) == 1
        assert len(store.list_keys()) == 3

    def test_delete_key(self, store):
        _, metadata = store.create_key("user1")
        assert store.delete_key(metadata.key_id) is True
        assert store.get_key(metadata.key_id) is None

    def test_delete_nonexistent_key(self, store):
        assert store.delete_key("nonexistent") is False

    def test_key_uniqueness(self, store):
        raw1, _ = store.create_key("user1")
        raw2, _ = store.create_key("user1")
        assert raw1 != raw2


class TestValidateAPIKeyFunction:
    def test_validate_success(self):
        store = APIKeyStore()
        raw_key, _ = store.create_key("user1")
        result = validate_api_key(store, raw_key)
        assert result is not None

    def test_validate_failure(self):
        store = APIKeyStore()
        result = validate_api_key(store, "pk_invalid")
        assert result is None
