"""Complete auth module tests."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import (
    APIAuth, AuthMiddleware, TokenManager, TokenPayload,
    AuthConfig, PermissionChecker, RoleBasedAccess,
    create_auth_middleware, authenticate_request,
    validate_token, generate_token, revoke_token,
)


class TestAuthComplete:
    def test_all_exports(self):
        assert APIAuth is not None
        assert AuthMiddleware is not None
        assert TokenManager is not None
        assert TokenPayload is not None
        assert AuthConfig is not None
        assert PermissionChecker is not None
        assert RoleBasedAccess is not None

    def test_all_factories(self):
        mw = create_auth_middleware()
        assert mw is not None

    def test_all_helpers(self):
        auth = APIAuth()
        token = generate_token(auth, "user1", ["read"])
        assert token is not None
        payload = validate_token(auth, token)
        assert payload is not None
        assert revoke_token(auth, token) is True

    def test_full_workflow(self):
        auth = APIAuth()
        auth.rbac.add_role("admin", ["read", "write", "delete"])
        auth.rbac.assign_role("user1", "admin")
        token = auth.generate_token("user1", ["read", "write"])
        payload = auth.validate_token(token)
        assert payload.user_id == "user1"
        assert auth.check_permission("user1", payload.permissions, "write")
        assert auth.rbac.has_permission("user1", "delete")
