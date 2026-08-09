"""Tests for auth middleware."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import AuthMiddleware


class TestAuthMiddleware:
    def test_no_auth_header(self):
        mw = AuthMiddleware()
        result = mw.process_request({"headers": {}})
        assert result["authenticated"] is False
        assert "Missing" in result["error"]

    def test_wrong_auth_format(self):
        mw = AuthMiddleware()
        result = mw.process_request({"headers": {"Authorization": "Basic abc"}})
        assert result["authenticated"] is False
        assert "Invalid" in result["error"]

    def test_valid_bearer_token(self):
        mw = AuthMiddleware()
        token = mw.auth.generate_token("user1", ["read", "write"])
        result = mw.process_request({"headers": {"Authorization": f"Bearer {token}"}})
        assert result["authenticated"] is True
        assert result["user_id"] == "user1"
        assert "read" in result["permissions"]

    def test_expired_token(self):
        mw = AuthMiddleware()
        from personal_index.content_api_auth import AuthConfig, TokenManager
        config = AuthConfig(token_expiry=0)
        auth = mw.auth
        auth.config = config
        auth.token_manager = TokenManager(secret_key=config.secret_key)
        mw.token_manager = auth.token_manager
        token = auth.generate_token("user1", ["read"])
        result = mw.process_request({"headers": {"Authorization": f"Bearer {token}"}})
        assert result["authenticated"] is False
