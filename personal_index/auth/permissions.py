"""Permission and role management for personal-index."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set


class Permission(Enum):
    """Built-in permissions for the system."""
    READ_INDEX = "read:index"
    WRITE_INDEX = "write:index"
    DELETE_INDEX = "delete:index"
    READ_CONFIG = "read:config"
    WRITE_CONFIG = "write:config"
    READ_STATS = "read:stats"
    MANAGE_USERS = "manage:users"
    MANAGE_KEYS = "manage:keys"
    RUN_CRAWL = "run:crawl"
    VIEW_DASHBOARD = "view:dashboard"


class Role(Enum):
    """Built-in roles with predefined permission sets."""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    CRAWLER = "crawler"


# Default permission mappings for roles
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.EDITOR: {
        Permission.READ_INDEX,
        Permission.WRITE_INDEX,
        Permission.DELETE_INDEX,
        Permission.READ_CONFIG,
        Permission.READ_STATS,
        Permission.VIEW_DASHBOARD,
    },
    Role.VIEWER: {
        Permission.READ_INDEX,
        Permission.READ_STATS,
        Permission.VIEW_DASHBOARD,
    },
    Role.CRAWLER: {
        Permission.READ_INDEX,
        Permission.RUN_CRAWL,
        Permission.READ_STATS,
    },
}


@dataclass
class User:
    """Represents a user with roles and permissions."""
    user_id: str
    username: str
    roles: List[Role] = field(default_factory=list)
    extra_permissions: List[Permission] = field(default_factory=list)
    is_active: bool = True

    def get_permissions(self) -> Set[Permission]:
        """Get all permissions for this user."""
        perms: Set[Permission] = set()
        for role in self.roles:
            perms.update(ROLE_PERMISSIONS.get(role, set()))
        perms.update(self.extra_permissions)
        return perms


class PermissionChecker:
    """Checks if a user has specific permissions."""

    def __init__(self, custom_role_permissions: Dict[Role, Set[Permission]] | None = None):
        self._role_permissions = custom_role_permissions or ROLE_PERMISSIONS.copy()

    def check(self, user: User, permission: Permission) -> bool:
        """Check if a user has a specific permission.

        Args:
            user: The user to check.
            permission: The permission to verify.

        Returns:
            True if user has the permission.
        """
        if not user.is_active:
            return False
        return permission in user.get_permissions()

    def check_any(self, user: User, *permissions: Permission) -> bool:
        """Check if user has any of the given permissions.

        Args:
            user: The user to check.
            *permissions: Permissions to check against.

        Returns:
            True if user has at least one of the permissions.
        """
        if not user.is_active:
            return False
        user_perms = user.get_permissions()
        return bool(user_perms & set(permissions))

    def check_all(self, user: User, *permissions: Permission) -> bool:
        """Check if user has all of the given permissions.

        Args:
            user: The user to check.
            *permissions: Permissions to check against.

        Returns:
            True if user has all of the permissions.
        """
        if not user.is_active:
            return False
        user_perms = user.get_permissions()
        return set(permissions).issubset(user_perms)

    def add_role_permissions(self, role: Role, permissions: Set[Permission]) -> None:
        """Add custom permissions to a role.

        Args:
            role: The role to modify.
            permissions: Permissions to add.
        """
        if role not in self._role_permissions:
            self._role_permissions[role] = set()
        self._role_permissions[role].update(permissions)

    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get permissions for a role.

        Args:
            role: The role to query.

        Returns:
            Set of permissions for the role.
        """
        return self._role_permissions.get(role, set()).copy()
