"""Tests for auth session management."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import TokenManager, APIAuth


class TestAuthSessions:
    def test_multiple_tokens_same_user(self):
        tm = TokenManager(max_tokens_per_user=5)
        tokens = []
        for i in range(5):
            token = tm.generate_token("user1", [f"perm_{i}"])
            tokens.append(token)
        assert len(tokens) == 5

    def test_exceed_max_tokens(self):
        tm = TokenManager(max_tokens_per_user=2)
        tm.generate_token("user1", ["read"])
        tm.generate_token("user1", ["write"])
        result = tm.generate_token("user1", ["delete"])
        assert result is None

    def test_list_active_tokens(self):
        tm = TokenManager(max_tokens_per_user=5)
        t1 = tm.generate_token("user1", ["read"])
        t2 = tm.generate_token("user1", ["write"])
        tokens = tm.list_tokens("user1")
        assert len(tokens) == 2

    def test_revoked_not_in_list(self):
        tm = TokenManager(max_tokens_per_user=5)
        t1 = tm.generate_token("user1", ["read"])
        t2 = tm.generate_token("user1", ["write"])
        tm.revoke_token(t1)
        tokens = tm.list_tokens("user1")
        assert len(tokens) == 1
        assert t2 in tokens
