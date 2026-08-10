"""Authentication system for personal-index."""

from personal_index.auth.api_keys import (
    APIKey,
    APIKeyStore,
    validate_api_key,
)
from personal_index.auth.passwords import (
    PasswordConfig,
    hash_password,
    verify_password,
)
from personal_index.auth.permissions import (
    Permission,
    PermissionChecker,
    Role,
)
from personal_index.auth.sessions import (
    Session,
    SessionStore,
)
from personal_index.auth.tokens import (
    JWTManager,
    TokenPayload,
    generate_token,
    verify_token,
)

__all__ = [
    "APIKey",
    "APIKeyStore",
    "JWTManager",
    "PasswordConfig",
    "Permission",
    "PermissionChecker",
    "Role",
    "Session",
    "SessionStore",
    "TokenPayload",
    "generate_token",
    "hash_password",
    "validate_api_key",
    "verify_password",
    "verify_token",
]
