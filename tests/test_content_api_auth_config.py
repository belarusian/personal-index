"""Tests for auth configuration."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import AuthConfig, APIAuth


class TestAuthConfig:
    def test_default_expiry(self):
        config = AuthConfig()
        assert config.token_expiry == 3600

    def test_default_max_tokens(self):
        config = AuthConfig()
        assert config.max_tokens_per_user == 10

    def test_custom_expiry(self):
        config = AuthConfig(token_expiry=7200)
        assert config.token_expiry == 7200

    def test_custom_max_tokens(self):
        config = AuthConfig(max_tokens_per_user=5)
        assert config.max_tokens_per_user == 5

    def test_config_serialization(self):
        config = AuthConfig()
        d = config.to_dict()
        assert "token_expiry" in d
        assert "max_tokens_per_user" in d

    def test_auth_uses_config(self):
        config = AuthConfig(token_expiry=1800)
        auth = APIAuth(config=config)
        assert auth.config.token_expiry == 1800
