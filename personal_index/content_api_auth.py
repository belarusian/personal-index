"""API authentication for personal-index content API."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import json
import base64
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TokenPayload:
    """Payload data embedded in an auth token."""
    user_id: str
    permissions: list[str] = field(default_factory=list)
    expires_in: int = 3600
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "permissions": self.permissions,
            "expires_in": self.expires_in,
            "created_at": self.created_at,
        }


@dataclass
class AuthConfig:
    """Configuration for the authentication system."""
    token_expiry: int = 3600
    max_tokens_per_user: int = 10
    secret_key: str = field(default_factory=lambda: secrets.token_hex(32))

    def to_dict(self) -> dict:
        return {
            "token_expiry": self.token_expiry,
            "max_tokens_per_user": self.max_tokens_per_user,
        }


class TokenManager:
    """Manages authentication tokens with generation, validation, and revocation."""

    def __init__(self, secret_key: Optional[str] = None, max_tokens_per_user: int = 10):
        self._secret = secret_key or secrets.token_hex(32)
        self._tokens: dict[str, TokenPayload] = {}
        self._revoked: set[str] = set()
        self._user_tokens: dict[str, list[str]] = {}
        self._max_tokens = max_tokens_per_user

    def generate_token(self, user_id: str, permissions: list[str]) -> Optional[str]:
        """Generate a new authentication token.

        Args:
            user_id: The user identifier.
            permissions: List of permission strings.

        Returns:
            Token string or None if max tokens reached.
        """
        current_count = len(self._user_tokens.get(user_id, []))
        if current_count >= self._max_tokens:
            return None

        payload = TokenPayload(user_id=user_id, permissions=permissions)
        payload_dict = payload.to_dict()
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload_dict).encode()
        ).decode()
        signature = hmac.new(
            self._secret.encode(), encoded.encode(), hashlib.sha256
        ).hexdigest()[:16]
        token = f"{encoded}.{signature}"
        self._tokens[token] = payload
        if user_id not in self._user_tokens:
            self._user_tokens[user_id] = []
        self._user_tokens[user_id].append(token)
        return token

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validate a token and return its payload.

        Args:
            token: The token string to validate.

        Returns:
            TokenPayload if valid, None otherwise.
        """
        if token in self._revoked:
            return None

        payload = self._tokens.get(token)
        if payload is None:
            return None

        # Verify signature
        parts = token.split(".")
        if len(parts) != 2:
            return None
        encoded, sig = parts
        expected_sig = hmac.new(
            self._secret.encode(), encoded.encode(), hashlib.sha256
        ).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected_sig):
            return None

        # Check expiry
        if time.time() - payload.created_at > payload.expires_in:
            return None

        return payload

    def revoke_token(self, token: str) -> bool:
        """Revoke a token.

        Args:
            token: The token to revoke.

        Returns:
            True if revoked, False if not found.
        """
        if token in self._tokens:
            self._revoked.add(token)
            payload = self._tokens[token]
            user_tokens = self._user_tokens.get(payload.user_id, [])
            if token in user_tokens:
                user_tokens.remove(token)
            return True
        return False

    def list_tokens(self, user_id: str) -> list[str]:
        """List active tokens for a user.

        Args:
            user_id: The user identifier.

        Returns:
            List of active token strings.
        """
        tokens = self._user_tokens.get(user_id, [])
        return [t for t in tokens if t not in self._revoked]


class PermissionChecker:
    """Checks permissions against a list of granted permissions."""

    def check(self, granted: list[str], required: str) -> bool:
        """Check if a required permission is granted.

        Args:
            granted: List of granted permissions.
            required: The permission to check.

        Returns:
            True if permission is granted.
        """
        if "*" in granted:
            return True
        return required in granted

    def check_any(self, granted: list[str], required: list[str]) -> bool:
        """Check if any of the required permissions are granted.

        Args:
            granted: List of granted permissions.
            required: List of required permissions.

        Returns:
            True if any permission matches.
        """
        if "*" in granted:
            return True
        return bool(set(granted) & set(required))

    def check_all(self, granted: list[str], required: list[str]) -> bool:
        """Check if all required permissions are granted.

        Args:
            granted: List of granted permissions.
            required: List of required permissions.

        Returns:
            True if all permissions are granted.
        """
        if "*" in granted:
            return True
        return set(required).issubset(set(granted))


class RoleBasedAccess:
    """Role-based access control system."""

    def __init__(self):
        self._roles: dict[str, list[str]] = {}
        self._user_roles: dict[str, list[str]] = {}

    def add_role(self, role_name: str, permissions: list[str]) -> None:
        """Define a role with its permissions.

        Args:
            role_name: The role name.
            permissions: List of permissions for this role.
        """
        self._roles[role_name] = list(permissions)

    def get_role_permissions(self, role_name: str) -> list[str]:
        """Get permissions for a role.

        Args:
            role_name: The role name.

        Returns:
            List of permissions.
        """
        return list(self._roles.get(role_name, []))

    def assign_role(self, user_id: str, role_name: str) -> None:
        """Assign a role to a user.

        Args:
            user_id: The user identifier.
            role_name: The role to assign.
        """
        if user_id not in self._user_roles:
            self._user_roles[user_id] = []
        if role_name not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role_name)

    def get_user_roles(self, user_id: str) -> list[str]:
        """Get roles assigned to a user.

        Args:
            user_id: The user identifier.

        Returns:
            List of role names.
        """
        return list(self._user_roles.get(user_id, []))

    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission.

        Args:
            user_id: The user identifier.
            permission: The permission to check.

        Returns:
            True if the user has the permission.
        """
        roles = self.get_user_roles(user_id)
        for role in roles:
            perms = self.get_role_permissions(role)
            if permission in perms:
                return True
        return False

    def remove_role_from_user(self, user_id: str, role_name: str) -> None:
        """Remove a role from a user.

        Args:
            user_id: The user identifier.
            role_name: The role to remove.
        """
        user_roles = self._user_roles.get(user_id, [])
        if role_name in user_roles:
            user_roles.remove(role_name)


class APIAuth:
    """Main authentication API class."""

    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        self.token_manager = TokenManager(
            secret_key=self.config.secret_key,
            max_tokens_per_user=self.config.max_tokens_per_user,
        )
        self.permission_checker = PermissionChecker()
        self.rbac = RoleBasedAccess()

    def generate_token(self, user_id: str, permissions: list[str]) -> Optional[str]:
        """Generate a new auth token.

        Args:
            user_id: The user identifier.
            permissions: List of permissions.

        Returns:
            Token string or None.
        """
        return self.token_manager.generate_token(user_id, permissions)

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Validate a token.

        Args:
            token: The token string.

        Returns:
            TokenPayload if valid, None otherwise.
        """
        return self.token_manager.validate_token(token)

    def check_permission(self, user_id: str, permissions: list[str], required: str) -> bool:
        """Check if a user has a required permission.

        Args:
            user_id: The user identifier.
            permissions: User's granted permissions.
            required: The required permission.

        Returns:
            True if permission is granted.
        """
        return self.permission_checker.check(permissions, required)


class AuthMiddleware:
    """Middleware for processing authentication on incoming requests."""

    def __init__(self):
        self.token_manager = TokenManager()
        self.auth = APIAuth()
        # Share the same token manager between middleware and auth
        self.auth.token_manager = self.token_manager

    def process_request(self, request: dict) -> dict:
        """Process an incoming request for authentication.

        Args:
            request: Request dict with headers.

        Returns:
            Dict with authentication result.
        """
        headers = request.get("headers", {})
        auth_header = headers.get("Authorization", "")

        if not auth_header:
            return {"authenticated": False, "error": "Missing Authorization header"}

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != "Bearer":
            return {"authenticated": False, "error": "Invalid Authorization format"}

        token = parts[1]
        payload = self.auth.validate_token(token)

        if payload is None:
            return {"authenticated": False, "error": "Invalid or expired token"}

        return {
            "authenticated": True,
            "user_id": payload.user_id,
            "permissions": payload.permissions,
        }


def create_auth_middleware() -> AuthMiddleware:
    """Factory function to create auth middleware.

    Returns:
        AuthMiddleware instance.
    """
    return AuthMiddleware()


def authenticate_request(auth: APIAuth, token: str) -> dict:
    """Authenticate a request using a token.

    Args:
        auth: The APIAuth instance.
        token: The token string.

    Returns:
        Dict with authentication result.
    """
    payload = auth.validate_token(token)
    if payload is None:
        return {"authenticated": False, "error": "Invalid token"}
    return {
        "authenticated": True,
        "user_id": payload.user_id,
        "permissions": payload.permissions,
    }


def validate_token(auth: APIAuth, token: str) -> Optional[TokenPayload]:
    """Validate a token using the auth instance.

    Args:
        auth: The APIAuth instance.
        token: The token string.

    Returns:
        TokenPayload if valid, None otherwise.
    """
    return auth.validate_token(token)


def generate_token(auth: APIAuth, user_id: str, permissions: list[str]) -> Optional[str]:
    """Generate a token using the auth instance.

    Args:
        auth: The APIAuth instance.
        user_id: The user identifier.
        permissions: List of permissions.

    Returns:
        Token string or None.
    """
    return auth.generate_token(user_id, permissions)


def revoke_token(auth: APIAuth, token: str) -> bool:
    """Revoke a token using the auth instance.

    Args:
        auth: The APIAuth instance.
        token: The token string.

    Returns:
        True if revoked.
    """
    return auth.token_manager.revoke_token(token)
