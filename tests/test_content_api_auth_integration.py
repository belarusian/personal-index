"""Integration tests for auth module."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import (
    APIAuth, AuthMiddleware, RoleBasedAccess,
    PermissionChecker, TokenManager,
)


class TestAuthIntegration:
    def test_auth_with_rbac(self):
        auth = APIAuth()
        auth.rbac.add_role("admin", ["read", "write", "delete"])
        auth.rbac.assign_role("user1", "admin")
        token = auth.generate_token("user1", ["read"])
        payload = auth.validate_token(token)
        assert payload is not None
        assert auth.rbac.has_permission("user1", "delete")

    def test_middleware_with_rbac(self):
        mw = AuthMiddleware()
        mw.auth.rbac.add_role("admin", ["read", "write"])
        mw.auth.rbac.assign_role("user1", "admin")
        token = mw.auth.generate_token("user1", ["read"])
        result = mw.process_request(
            {"headers": {"Authorization": f"Bearer {token}"}}
        )
        assert result["authenticated"] is True

    def test_full_lifecycle(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        payload = auth.validate_token(token)
        assert payload is not None
        assert auth.check_permission("user1", payload.permissions, "read")
        assert auth.token_manager.revoke_token(token)
        assert auth.validate_token(token) is None
