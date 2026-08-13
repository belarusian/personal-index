"""Tests for permission management."""

from personal_index.auth.permissions import (
    Permission,
    PermissionChecker,
    Role,
    ROLE_PERMISSIONS,
    User,
)


class TestUser:
    def test_default(self):
        u = User(user_id="1", username="alice")
        assert u.is_active is True
        assert u.roles == []

    def test_get_permissions_admin(self):
        u = User(user_id="1", username="admin", roles=[Role.ADMIN])
        perms = u.get_permissions()
        assert Permission.READ_INDEX in perms

    def test_extra_permissions(self):
        u = User(
            user_id="1",
            username="alice",
            roles=[],
            extra_permissions=[Permission.WRITE_INDEX],
        )
        perms = u.get_permissions()
        assert Permission.WRITE_INDEX in perms

    def test_empty_roles_no_extra(self):
        u = User(user_id="1", username="nobody")
        assert u.get_permissions() == set()


class TestPermissionChecker:
    def _make_checker(self):
        custom = {r: set(p) for r, p in ROLE_PERMISSIONS.items()}
        return PermissionChecker(custom_role_permissions=custom)

    def test_check_active_admin(self):
        checker = self._make_checker()
        user = User(user_id="1", username="admin", roles=[Role.ADMIN])
        assert checker.check(user, Permission.READ_INDEX) is True

    def test_check_inactive_user(self):
        checker = self._make_checker()
        user = User(user_id="1", username="admin", roles=[Role.ADMIN], is_active=False)
        assert checker.check(user, Permission.READ_INDEX) is False

    def test_check_extra_permission(self):
        checker = self._make_checker()
        user = User(user_id="1", username="alice", roles=[], extra_permissions=[Permission.RUN_CRAWL])
        assert checker.check(user, Permission.RUN_CRAWL) is True

    def test_check_any(self):
        checker = self._make_checker()
        user = User(user_id="1", username="alice", roles=[], extra_permissions=[Permission.READ_INDEX])
        assert checker.check_any(user, Permission.WRITE_INDEX, Permission.READ_INDEX) is True

    def test_check_any_none(self):
        checker = self._make_checker()
        user = User(user_id="1", username="alice", roles=[], extra_permissions=[Permission.READ_INDEX])
        assert checker.check_any(user, Permission.MANAGE_USERS, Permission.MANAGE_KEYS) is False

    def test_check_all(self):
        checker = self._make_checker()
        user = User(user_id="1", username="admin", roles=[Role.ADMIN])
        assert checker.check_all(user, Permission.READ_INDEX, Permission.WRITE_CONFIG) is True

    def test_check_all_missing_one(self):
        checker = self._make_checker()
        user = User(user_id="1", username="alice", roles=[], extra_permissions=[Permission.READ_INDEX])
        assert checker.check_all(user, Permission.READ_INDEX, Permission.WRITE_INDEX) is False

    def test_add_role_permissions(self):
        custom = {r: set(p) for r, p in ROLE_PERMISSIONS.items()}
        checker = PermissionChecker(custom_role_permissions=custom)
        checker.add_role_permissions(Role.VIEWER, {Permission.WRITE_INDEX})
        viewer_perms = checker.get_role_permissions(Role.VIEWER)
        assert Permission.WRITE_INDEX in viewer_perms

    def test_get_role_permissions(self):
        custom = {r: set(p) for r, p in ROLE_PERMISSIONS.items()}
        checker = PermissionChecker(custom_role_permissions=custom)
        perms = checker.get_role_permissions(Role.ADMIN)
        assert Permission.READ_INDEX in perms


class TestRolePermissions:
    def test_roles_defined(self):
        assert Role.ADMIN.value == "admin"
        assert Role.EDITOR.value == "editor"
        assert Role.VIEWER.value == "viewer"
        assert Role.CRAWLER.value == "crawler"

    def test_permissions_defined(self):
        assert Permission.READ_INDEX.value == "read:index"
