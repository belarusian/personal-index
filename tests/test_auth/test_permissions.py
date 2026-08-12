"""Tests for permission and role management."""

from __future__ import annotations

import pytest

from personal_index.auth.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    PermissionChecker,
    Role,
    User,
)


@pytest.fixture
def checker():
    return PermissionChecker()


class TestUser:
    def test_create_user(self):
        user = User(user_id="u1", username="alice", roles=[Role.ADMIN])
        assert user.user_id == "u1"
        assert user.is_active is True

    def test_user_permissions_admin(self):
        user = User(user_id="u1", username="alice", roles=[Role.ADMIN])
        perms = user.get_permissions()
        assert perms == set(Permission)

    def test_user_permissions_viewer(self):
        user = User(user_id="u1", username="bob", roles=[Role.VIEWER])
        perms = user.get_permissions()
        assert Permission.READ_INDEX in perms
        assert Permission.WRITE_INDEX not in perms

    def test_user_extra_permissions(self):
        user = User(
            user_id="u1",
            username="bob",
            roles=[Role.VIEWER],
            extra_permissions=[Permission.WRITE_INDEX],
        )
        perms = user.get_permissions()
        assert Permission.WRITE_INDEX in perms

    def test_inactive_user_permissions(self):
        user = User(user_id="u1", username="bob", roles=[Role.ADMIN], is_active=False)
        perms = user.get_permissions()
        assert len(perms) > 0  # Still returns perms, checker handles active check


class TestPermissionChecker:
    def test_check_admin_has_all(self, checker):
        user = User(user_id="u1", username="admin", roles=[Role.ADMIN])
        for perm in Permission:
            assert checker.check(user, perm) is True

    def test_check_viewer_cannot_write(self, checker):
        user = User(user_id="u1", username="viewer", roles=[Role.VIEWER])
        assert checker.check(user, Permission.WRITE_INDEX) is False
        assert checker.check(user, Permission.READ_INDEX) is True

    def test_check_inactive_user(self, checker):
        user = User(user_id="u1", username="inactive", roles=[Role.ADMIN], is_active=False)
        assert checker.check(user, Permission.READ_INDEX) is False

    def test_check_any(self, checker):
        user = User(user_id="u1", username="viewer", roles=[Role.VIEWER])
        assert checker.check_any(
            user, Permission.WRITE_INDEX, Permission.READ_INDEX
        ) is True
        assert checker.check_any(
            user, Permission.WRITE_INDEX, Permission.DELETE_INDEX
        ) is False

    def test_check_all(self, checker):
        user = User(user_id="u1", username="viewer", roles=[Role.VIEWER])
        assert checker.check_all(
            user, Permission.READ_INDEX, Permission.READ_STATS
        ) is True
        assert checker.check_all(
            user, Permission.READ_INDEX, Permission.WRITE_INDEX
        ) is False

    def test_add_role_permissions(self, checker):
        checker.add_role_permissions(
            Role.VIEWER, {Permission.WRITE_INDEX}
        )
        user = User(user_id="u1", username="viewer", roles=[Role.VIEWER])
        assert checker.check(user, Permission.WRITE_INDEX) is True

    def test_get_role_permissions(self, checker):
        perms = checker.get_role_permissions(Role.ADMIN)
        assert perms == set(Permission)

    def test_crawler_role(self, checker):
        user = User(user_id="u1", username="crawler", roles=[Role.CRAWLER])
        assert checker.check(user, Permission.RUN_CRAWL) is True
        assert checker.check(user, Permission.WRITE_INDEX) is False


class TestRolePermissions:
    def test_editor_permissions(self):
        editor_perms = ROLE_PERMISSIONS[Role.EDITOR]
        assert Permission.WRITE_INDEX in editor_perms
        assert Permission.MANAGE_USERS not in editor_perms

    def test_viewer_permissions(self):
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.READ_INDEX in viewer_perms
        assert Permission.DELETE_INDEX not in viewer_perms
