"""Tests for JWT token management."""

from __future__ import annotations

import time

import pytest

from personal_index.auth.tokens import (
    JWTManager,
    TokenPayload,
    generate_token,
    verify_token,
)


@pytest.fixture
def secret():
    return "test-secret-key-for-jwt-signing"


@pytest.fixture
def manager(secret):
    return JWTManager(secret, default_ttl=3600)


class TestTokenPayload:
    def test_create_payload(self):
        payload = TokenPayload(sub="user123")
        assert payload.sub == "user123"
        assert payload.exp is None
        assert payload.roles == []
        assert payload.metadata == {}

    def test_payload_to_dict(self):
        payload = TokenPayload(sub="user123", roles=["admin"])
        data = payload.to_dict()
        assert data["sub"] == "user123"
        assert data["roles"] == ["admin"]
        assert "exp" not in data

    def test_payload_from_dict(self):
        data = {"sub": "user456", "roles": ["editor"], "iat": 123456.0}
        payload = TokenPayload.from_dict(data)
        assert payload.sub == "user456"
        assert payload.roles == ["editor"]

    def test_payload_with_exp(self):
        payload = TokenPayload(sub="user123", exp=time.time() + 3600)
        data = payload.to_dict()
        assert "exp" in data
        assert data["exp"] > time.time()


class TestJWTManager:
    def test_create_token(self, manager):
        token = manager.create_token("user123")
        assert isinstance(token, str)
        assert "." in token
        parts = token.split(".")
        assert len(parts) == 3

    def test_verify_valid_token(self, manager):
        token = manager.create_token("user123", roles=["admin"])
        payload = manager.verify_token(token)
        assert payload is not None
        assert payload.sub == "user123"
        assert payload.roles == ["admin"]

    def test_verify_token_with_metadata(self, manager):
        token = manager.create_token("user123", metadata={"org": "acme"})
        payload = manager.verify_token(token)
        assert payload is not None
        assert payload.metadata == {"org": "acme"}

    def test_verify_invalid_token(self, manager):
        payload = manager.verify_token("invalid.token.here")
        assert payload is None

    def test_verify_tampered_token(self, manager):
        token = manager.create_token("user123")
        parts = token.split(".")
        parts[1] = "tampered"
        tampered = ".".join(parts)
        payload = manager.verify_token(tampered)
        assert payload is None

    def test_verify_wrong_secret(self, manager):
        token = manager.create_token("user123")
        other_manager = JWTManager("different-secret")
        payload = other_manager.verify_token(token)
        assert payload is None

    def test_expired_token(self, manager):
        token = manager.create_token("user123", ttl=0)
        time.sleep(0.01)
        payload = manager.verify_token(token)
        assert payload is None

    def test_blacklist_token(self, manager):
        token = manager.create_token("user123")
        assert manager.verify_token(token) is not None
        manager.blacklist_token(token)
        assert manager.verify_token(token) is None

    def test_blacklist_already_blacklisted(self, manager):
        token = manager.create_token("user123")
        assert manager.blacklist_token(token) is True
        assert manager.blacklist_token(token) is False

    def test_custom_ttl(self, manager):
        token = manager.create_token("user123", ttl=7200)
        payload = manager.verify_token(token)
        assert payload is not None
        assert payload.exp is not None
        assert payload.exp > time.time() + 7000

    def test_unique_jti(self, manager):
        token1 = manager.create_token("user123")
        token2 = manager.create_token("user123")
        p1 = manager.verify_token(token1)
        p2 = manager.verify_token(token2)
        assert p1 is not None and p2 is not None
        assert p1.jti != p2.jti


class TestConvenienceFunctions:
    def test_generate_token(self):
        token = generate_token("secret", "user1", ttl=600)
        assert isinstance(token, str)
        assert "." in token

    def test_verify_token_success(self):
        token = generate_token("secret", "user1", roles=["admin"])
        payload = verify_token(token, "secret")
        assert payload is not None
        assert payload.sub == "user1"
        assert payload.roles == ["admin"]

    def test_verify_token_wrong_secret(self):
        token = generate_token("secret", "user1")
        payload = verify_token(token, "wrong-secret")
        assert payload is None

    def test_verify_token_expired(self):
        token = generate_token("secret", "user1", ttl=0)
        time.sleep(0.01)
        payload = verify_token(token, "secret")
        assert payload is None
