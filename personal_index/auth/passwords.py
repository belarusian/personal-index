"""Password hashing and verification for personal-index."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Optional


@dataclass
class PasswordConfig:
    """Configuration for password hashing."""
    algorithm: str = "sha256"
    iterations: int = 100_000
    salt_length: int = 32
    key_length: int = 32


def _generate_salt(length: int = 32) -> str:
    """Generate a cryptographically secure random salt."""
    return secrets.token_hex(length)


def _hash_with_salt(password: str, salt: str, iterations: int = 100_000) -> str:
    """Hash a password with a salt using PBKDF2-HMAC-SHA256."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
        dklen=32,
    )
    return dk.hex()


def hash_password(
    password: str,
    config: Optional[PasswordConfig] = None,
) -> str:
    """Hash a password with a random salt.

    The returned hash string format is:
    algorithm$iterations$salt$hash

    Args:
        password: The plaintext password.
        config: Optional password configuration.

    Returns:
        Hashed password string.
    """
    actual_config = config or PasswordConfig()
    salt = _generate_salt(actual_config.salt_length)
    password_hash = _hash_with_salt(password, salt, actual_config.iterations)
    return f"{actual_config.algorithm}${actual_config.iterations}${salt}${password_hash}"


def verify_password(
    password: str,
    hashed_password: str,
    config: Optional[PasswordConfig] = None,
) -> bool:
    """Verify a password against a hashed password.

    Args:
        password: The plaintext password to verify.
        hashed_password: The stored hash string.
        config: Optional password configuration.

    Returns:
        True if the password matches.
    """
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4:
            return False
        algorithm, iterations_str, salt, stored_hash = parts
        iterations = int(iterations_str)
        computed_hash = _hash_with_salt(password, salt, iterations)
        return secrets.compare_digest(computed_hash, stored_hash)
    except (ValueError, IndexError):
        return False


def is_valid_password(password: str, min_length: int = 8) -> tuple[bool, list[str]]:
    """Validate password strength.

    Args:
        password: The password to validate.
        min_length: Minimum required length.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors = []
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain an uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain a lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain a digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain a special character")
    return len(errors) == 0, errors
