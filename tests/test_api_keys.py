"""Tests for API key management."""

from datetime import datetime, timedelta, timezone

from personal_index.auth.api_keys import (
    APIKeyStore,
    validate_api_key,
)


class TestAPIKeyStore:
    def test_create_key(self):
        store = APIKeyStore()
        raw, key = store.create_key("owner1", name="test-key")
        assert raw.startswith("pk_")
        assert key.name == "test-key"

    def test_validate_key(self):
        store = APIKeyStore()
        raw, _ = store.create_key("owner1")
        key = store.validate_key(raw)
        assert key is not None
        assert key.owner == "owner1"

    def test_validate_invalid_key(self):
        store = APIKeyStore()
        assert store.validate_key("pk_invalidkey") is None

    def test_revoke_key(self):
        store = APIKeyStore()
        raw, key = store.create_key("owner1")
        assert store.revoke_key(key.key_id) is True
        assert store.validate_key(raw) is None

    def test_revoke_missing(self):
        store = APIKeyStore()
        assert store.revoke_key("missing") is False

    def test_get_key(self):
        store = APIKeyStore()
        _, key = store.create_key("owner1")
        got = store.get_key(key.key_id)
        assert got is not None

    def test_list_keys(self):
        store = APIKeyStore()
        store.create_key("owner1")
        store.create_key("owner2")
        assert len(store.list_keys(owner="owner1")) == 1

    def test_delete_key(self):
        store = APIKeyStore()
        _, key = store.create_key("owner1")
        assert store.delete_key(key.key_id) is True
        assert store.get_key(key.key_id) is None

    def test_delete_missing(self):
        store = APIKeyStore()
        assert store.delete_key("missing") is False

    def test_expired_key(self):
        store = APIKeyStore()
        exp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        raw, _ = store.create_key("owner1", expires_at=exp)
        assert store.validate_key(raw) is None

    def test_usage_count(self):
        store = APIKeyStore()
        raw, _ = store.create_key("owner1")
        store.validate_key(raw)
        store.validate_key(raw)
        key = store.validate_key(raw)
        assert key.usage_count == 3

    def test_custom_prefix(self):
        store = APIKeyStore()
        raw, _ = store.create_key("owner1", prefix="sk_")
        assert raw.startswith("sk_")

    def test_permissions(self):
        store = APIKeyStore()
        _, key = store.create_key("owner1", permissions=["read", "write"])
        assert key.permissions == ["read", "write"]


class TestValidateAPIKey:
    def test_convenience_function(self):
        store = APIKeyStore()
        raw, _ = store.create_key("owner1")
        key = validate_api_key(store, raw)
        assert key is not None
