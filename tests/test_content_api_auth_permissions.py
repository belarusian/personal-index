"""Tests for permission checking."""

from __future__ import annotations

import pytest
from personal_index.content_api_auth import PermissionChecker, APIAuth


class TestPermissionChecker:
    def test_single_permission_granted(self):
        pc = PermissionChecker()
        assert pc.check(["read"], "read") is True

    def test_single_permission_denied(self):
        pc = PermissionChecker()
        assert pc.check(["read"], "write") is False

    def test_wildcard_permission(self):
        pc = PermissionChecker()
        assert pc.check(["*"], "admin_action") is True

    def test_empty_permissions(self):
        pc = PermissionChecker()
        assert pc.check([], "read") is False

    def test_multiple_permissions(self):
        pc = PermissionChecker()
        assert pc.check(["read", "write", "delete"], "write") is True


class TestAPIAuthPermissions:
    def test_auth_check_permission(self):
        auth = APIAuth()
        assert auth.check_permission("user1", ["read"], "read") is True
        assert auth.check_permission("user1", ["read"], "write") is False

    def test_auth_wildcard(self):
        auth = APIAuth()
        assert auth.check_permission("user1", ["*"], "anything") is True
