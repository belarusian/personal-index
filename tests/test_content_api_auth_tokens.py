"""Tests for token management."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_auth import TokenManager, TokenPayload


class TestTokenGeneration:
    def test_token_format(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        parts = token.split(".")
        assert len(parts) == 2

    def test_token_uniqueness(self):
        tm = TokenManager()
        t1 = tm.generate_token("user1", ["read"])
        t2 = tm.generate_token("user1", ["read"])
        assert t1 != t2

    def test_token_different_users(self):
        tm = TokenManager()
        t1 = tm.generate_token("user1", ["read"])
        t2 = tm.generate_token("user2", ["read"])
        assert t1 != t2


class TestTokenValidation:
    def test_valid_token_returns_payload(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read", "write"])
        payload = tm.validate_token(token)
        assert payload.user_id == "user1"
        assert "read" in payload.permissions

    def test_tampered_token_rejected(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        parts = token.split(".")
        tampered = parts[0] + ".invalid_signature"
        assert tm.validate_token(tampered) is None

    def test_empty_string_rejected(self):
        tm = TokenManager()
        assert tm.validate_token("") is None

    def test_none_payload_fields(self):
        tm = TokenManager()
        token = tm.generate_token("user1", [])
        payload = tm.validate_token(token)
        assert payload.permissions == []


class TestTokenRevocation:
    def test_revoke_returns_true(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        assert tm.revoke_token(token) is True

    def test_revoke_unknown_returns_false(self):
        tm = TokenManager()
        assert tm.revoke_token("unknown_token") is False

    def test_revoke_twice(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        assert tm.revoke_token(token) is True
        assert tm.revoke_token(token) is False
