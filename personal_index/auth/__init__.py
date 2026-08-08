"""Authentication system for personal-index."""

from personal_index.auth.tokens import (
    JWTManager,
    TokenPayload,
    generate_token,
    verify_token,
)
from personal_index.auth.api_keys import (
    APIKeyStore,
    APIKey,
    validate_api_key,
)
from personal_index.auth.permissions import (
    Permission,
    Role,
    PermissionChecker,
)
from personal_index.auth.passwords import (
    hash_password,
    verify_password,
    PasswordConfig,
)
from personal_index.auth.sessions import (
    SessionStore,
    Session,
)

__all__ = [
    "JWTManager",
    "TokenPayload",
    "generate_token",
    "verify_token",
    "APIKeyStore",
    "APIKey",
    "validate_api_key",
    "Permission",
    "Role",
    "PermissionChecker",
    "hash_password",
    "verify_password",
    "PasswordConfig",
    "SessionStore",
    "Session",
]
