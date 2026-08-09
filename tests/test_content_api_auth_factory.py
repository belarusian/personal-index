"""Tests for auth factory functions."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import (
    create_auth_middleware,
    authenticate_request,
    validate_token,
    generate_token,
    revoke_token,
    APIAuth,
)


class TestAuthFactories:
    def test_create_middleware(self):
        mw = create_auth_middleware()
        assert mw is not None
        assert hasattr(mw, 'process_request')

    def test_authenticate_request_success(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        result = authenticate_request(auth, token)
        assert result["authenticated"] is True

    def test_authenticate_request_failure(self):
        auth = APIAuth()
        result = authenticate_request(auth, "bad_token")
        assert result["authenticated"] is False

    def test_validate_token_success(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        payload = validate_token(auth, token)
        assert payload is not None

    def test_generate_token_success(self):
        auth = APIAuth()
        token = generate_token(auth, "user1", ["read"])
        assert token is not None

    def test_revoke_token_success(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        assert revoke_token(auth, token) is True
