"""Tests for role-based access control."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import RoleBasedAccess, PermissionChecker


class TestRBAC:
    def test_multiple_roles(self):
        rbac = RoleBasedAccess()
        rbac.add_role("reader", ["read"])
        rbac.add_role("writer", ["read", "write"])
        rbac.assign_role("user1", "reader")
        rbac.assign_role("user1", "writer")
        assert rbac.has_permission("user1", "write") is True

    def test_role_inheritance(self):
        rbac = RoleBasedAccess()
        rbac.add_role("admin", ["read", "write", "delete"])
        rbac.assign_role("admin_user", "admin")
        assert rbac.has_permission("admin_user", "delete") is True

    def test_no_roles_no_permissions(self):
        rbac = RoleBasedAccess()
        assert rbac.has_permission("new_user", "read") is False


class TestPermissionChecker:
    def test_wildcard_allows_all(self):
        pc = PermissionChecker()
        assert pc.check(["*"], "anything") is True

    def test_specific_permission(self):
        pc = PermissionChecker()
        assert pc.check(["read"], "read") is True
        assert pc.check(["read"], "write") is False

    def test_check_any_matches_one(self):
        pc = PermissionChecker()
        assert pc.check_any(["read"], ["read", "write"]) is True

    def test_check_all_requires_all(self):
        pc = PermissionChecker()
        assert pc.check_all(["read", "write"], ["read", "write"]) is True
        assert pc.check_all(["read"], ["read", "write"]) is False
