"""Tests for content_api_auth module - API authentication."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import (
    APIAuth,
    AuthMiddleware,
    TokenManager,
    TokenPayload,
    AuthConfig,
    create_auth_middleware,
    authenticate_request,
    validate_token,
    generate_token,
    revoke_token,
    PermissionChecker,
    RoleBasedAccess,
)


class TestTokenPayload:
    def test_payload_basic(self):
        p = TokenPayload(user_id="user1", permissions=["read"])
        assert p.user_id == "user1"
        assert p.permissions == ["read"]

    def test_payload_with_expires(self):
        p = TokenPayload(user_id="user1", permissions=["read", "write"], expires_in=3600)
        assert p.expires_in == 3600

    def test_payload_to_dict(self):
        p = TokenPayload(user_id="user1", permissions=["read"])
        d = p.to_dict()
        assert d["user_id"] == "user1"
        assert d["permissions"] == ["read"]


class TestAuthConfig:
    def test_config_defaults(self):
        config = AuthConfig()
        assert config.token_expiry == 3600
        assert config.max_tokens_per_user == 10

    def test_config_custom(self):
        config = AuthConfig(token_expiry=7200, max_tokens_per_user=20)
        assert config.token_expiry == 7200
        assert config.max_tokens_per_user == 20

    def test_config_to_dict(self):
        config = AuthConfig()
        d = config.to_dict()
        assert "token_expiry" in d


class TestTokenManager:
    def test_manager_init(self):
        tm = TokenManager()
        assert tm is not None

    def test_generate_token(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_validate_token(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        payload = tm.validate_token(token)
        assert payload is not None
        assert payload.user_id == "user1"

    def test_validate_invalid_token(self):
        tm = TokenManager()
        payload = tm.validate_token("invalid_token_string")
        assert payload is None

    def test_revoke_token(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        result = tm.revoke_token(token)
        assert result is True

    def test_revoked_token_invalid(self):
        tm = TokenManager()
        token = tm.generate_token("user1", ["read"])
        tm.revoke_token(token)
        payload = tm.validate_token(token)
        assert payload is None

    def test_list_tokens(self):
        tm = TokenManager()
        tm.generate_token("user1", ["read"])
        tm.generate_token("user1", ["write"])
        tokens = tm.list_tokens("user1")
        assert len(tokens) == 2

    def test_list_tokens_empty(self):
        tm = TokenManager()
        tokens = tm.list_tokens("nonexistent")
        assert len(tokens) == 0

    def test_max_tokens_per_user(self):
        tm = TokenManager(max_tokens_per_user=2)
        tm.generate_token("user1", ["read"])
        tm.generate_token("user1", ["write"])
        result = tm.generate_token("user1", ["delete"])
        assert result is None


class TestAPIAuth:
    def test_auth_init(self):
        auth = APIAuth()
        assert auth is not None

    def test_auth_has_token_manager(self):
        auth = APIAuth()
        assert hasattr(auth, 'token_manager')

    def test_auth_generate_and_validate(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        payload = auth.validate_token(token)
        assert payload is not None
        assert payload.user_id == "user1"

    def test_auth_check_permission(self):
        auth = APIAuth()
        assert auth.check_permission("user1", ["read"], "read") is True
        assert auth.check_permission("user1", ["read"], "write") is False

    def test_auth_check_permission_admin(self):
        auth = APIAuth()
        assert auth.check_permission("user1", ["*"], "write") is True


class TestAuthMiddleware:
    def test_middleware_init(self):
        mw = AuthMiddleware()
        assert mw is not None

    def test_middleware_process_request(self):
        mw = AuthMiddleware()
        result = mw.process_request({"headers": {"Authorization": "Bearer token123"}})
        assert isinstance(result, dict)

    def test_middleware_missing_auth(self):
        mw = AuthMiddleware()
        result = mw.process_request({"headers": {}})
        assert result.get("authenticated") is False

    def test_middleware_invalid_token(self):
        mw = AuthMiddleware()
        result = mw.process_request({"headers": {"Authorization": "Bearer invalid"}})
        assert result.get("authenticated") is False

    def test_middleware_valid_token(self):
        mw = AuthMiddleware()
        token = mw.token_manager.generate_token("user1", ["read"])
        result = mw.process_request({"headers": {"Authorization": f"Bearer {token}"}})
        assert result.get("authenticated") is True


class TestPermissionChecker:
    def test_checker_init(self):
        checker = PermissionChecker()
        assert checker is not None

    def test_check_single_permission(self):
        checker = PermissionChecker()
        assert checker.check(["read"], "read") is True
        assert checker.check(["read"], "write") is False

    def test_check_wildcard(self):
        checker = PermissionChecker()
        assert checker.check(["*"], "anything") is True

    def test_check_empty_permissions(self):
        checker = PermissionChecker()
        assert checker.check([], "read") is False

    def test_check_any_permission(self):
        checker = PermissionChecker()
        assert checker.check_any(["read", "write"], ["read"]) is True
        assert checker.check_any(["read"], ["write"]) is False

    def test_check_all_permissions(self):
        checker = PermissionChecker()
        assert checker.check_all(["read", "write"], ["read", "write"]) is True
        assert checker.check_all(["read"], ["read", "write"]) is False


class TestRoleBasedAccess:
    def test_rbac_init(self):
        rbac = RoleBasedAccess()
        assert rbac is not None

    def test_add_role(self):
        rbac = RoleBasedAccess()
        rbac.add_role("admin", ["read", "write", "delete"])
        assert rbac.get_role_permissions("admin") == ["read", "write", "delete"]

    def test_get_unknown_role(self):
        rbac = RoleBasedAccess()
        perms = rbac.get_role_permissions("unknown")
        assert perms == []

    def test_assign_role(self):
        rbac = RoleBasedAccess()
        rbac.add_role("admin", ["read", "write"])
        rbac.assign_role("user1", "admin")
        assert rbac.get_user_roles("user1") == ["admin"]

    def test_check_user_permission(self):
        rbac = RoleBasedAccess()
        rbac.add_role("admin", ["read", "write"])
        rbac.assign_role("user1", "admin")
        assert rbac.has_permission("user1", "write") is True
        assert rbac.has_permission("user1", "delete") is False

    def test_remove_role(self):
        rbac = RoleBasedAccess()
        rbac.add_role("admin", ["read"])
        rbac.assign_role("user1", "admin")
        rbac.remove_role_from_user("user1", "admin")
        assert rbac.get_user_roles("user1") == []


class TestCreateAuthMiddleware:
    def test_create_returns_middleware(self):
        mw = create_auth_middleware()
        assert mw is not None


class TestAuthenticateRequest:
    def test_authenticate_with_token(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        result = authenticate_request(auth, token)
        assert result["authenticated"] is True

    def test_authenticate_invalid(self):
        auth = APIAuth()
        result = authenticate_request(auth, "invalid")
        assert result["authenticated"] is False


class TestValidateToken:
    def test_validate_token_function(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        payload = validate_token(auth, token)
        assert payload is not None


class TestGenerateToken:
    def test_generate_token_function(self):
        auth = APIAuth()
        token = generate_token(auth, "user1", ["read"])
        assert token is not None
        assert isinstance(token, str)


class TestRevokeToken:
    def test_revoke_token_function(self):
        auth = APIAuth()
        token = auth.generate_token("user1", ["read"])
        result = revoke_token(auth, token)
        assert result is True
