"""Edge case tests for auth module."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import TokenManager, APIAuth, RoleBasedAccess


class TestAuthEdgeCases:
    def test_empty_permissions(self):
        tm = TokenManager()
        token = tm.generate_token("user1", [])
        payload = tm.validate_token(token)
        assert payload.permissions == []

    def test_many_permissions(self):
        tm = TokenManager()
        perms = [f"perm_{i}" for i in range(50)]
        token = tm.generate_token("user1", perms)
        payload = tm.validate_token(token)
        assert len(payload.permissions) == 50

    def test_unicode_user_id(self):
        tm = TokenManager()
        token = tm.generate_token("пользователь", ["read"])
        payload = tm.validate_token(token)
        assert payload.user_id == "пользователь"

    def test_rbac_no_roles(self):
        rbac = RoleBasedAccess()
        assert rbac.has_permission("user1", "read") is False

    def test_rbac_remove_nonexistent_role(self):
        rbac = RoleBasedAccess()
        rbac.remove_role_from_user("user1", "admin")
        assert rbac.get_user_roles("user1") == []
