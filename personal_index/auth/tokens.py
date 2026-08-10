"""JWT token management for personal-index authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TokenPayload:
    """Payload data embedded in a JWT token."""
    sub: str  # subject (user identifier)
    iat: float = field(default_factory=time.time)  # issued at
    exp: float | None = None  # expiration
    jti: str = field(default_factory=lambda: uuid.uuid4().hex)  # unique token ID
    roles: list = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.exp is None:
            del data["exp"]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenPayload:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class JWTManager:
    """Manages JWT token creation and verification using HMAC-SHA256."""

    def __init__(self, secret: str, algorithm: str = "HS256", default_ttl: int = 3600):
        self._secret = secret
        self._algorithm = algorithm
        self._default_ttl = default_ttl
        self._blacklist: set = set()

    def create_token(
        self,
        subject: str,
        roles: list | None = None,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new JWT token.

        Args:
            subject: User identifier.
            roles: List of role names.
            ttl: Token time-to-live in seconds. Use 0 for immediately expired.
            metadata: Additional metadata to embed.

        Returns:
            Encoded JWT token string.
        """
        effective_ttl = self._default_ttl if ttl is None else ttl
        payload = TokenPayload(
            sub=subject,
            roles=roles or [],
            exp=time.time() + effective_ttl,
            metadata=metadata or {},
        )
        return self._encode(payload.to_dict())

    def verify_token(self, token: str) -> TokenPayload | None:
        """Verify and decode a JWT token.

        Args:
            token: The JWT token string.

        Returns:
            TokenPayload if valid, None otherwise.
        """
        if token in self._blacklist:
            return None
        payload_dict = self._decode(token)
        if payload_dict is None:
            return None
        # Check expiration
        if "exp" in payload_dict and payload_dict["exp"] < time.time():
            return None
        return TokenPayload.from_dict(payload_dict)

    def blacklist_token(self, token: str) -> bool:
        """Blacklist a token to prevent reuse.

        Args:
            token: The token to blacklist.

        Returns:
            True if token was blacklisted, False if already blacklisted.
        """
        if token in self._blacklist:
            return False
        self._blacklist.add(token)
        return True

    def _encode(self, payload: dict[str, Any]) -> str:
        """Encode payload into a JWT-like token using HMAC-SHA256."""
        header = {"alg": self._algorithm, "typ": "JWT"}
        header_b64 = self._base64url_encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = self._base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{header_b64}.{payload_b64}"
        signature = self._sign(signing_input)
        return f"{signing_input}.{signature}"

    def _decode(self, token: str) -> dict[str, Any] | None:
        """Decode and verify a JWT-like token."""
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature = parts
        signing_input = f"{header_b64}.{payload_b64}"
        if not self._verify_signature(signing_input, signature):
            return None
        try:
            payload_json = self._base64url_decode(payload_b64)
            return json.loads(payload_json)
        except (json.JSONDecodeError, ValueError):
            return None

    def _sign(self, data: str) -> str:
        """Create HMAC-SHA256 signature."""
        sig = hmac.new(
            self._secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._base64url_encode(sig)

    def _verify_signature(self, data: str, signature: str) -> bool:
        """Verify HMAC-SHA256 signature."""
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Base64url encode without padding, returning a string."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Base64url decode with padding restoration."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)


def generate_token(
    secret: str,
    subject: str,
    ttl: int = 3600,
    roles: list | None = None,
) -> str:
    """Convenience function to generate a JWT token.

    Args:
        secret: Signing secret.
        subject: User identifier.
        ttl: Token lifetime in seconds.
        roles: Optional roles list.

    Returns:
        Encoded JWT token.
    """
    manager = JWTManager(secret, default_ttl=ttl)
    return manager.create_token(subject, roles=roles)


def verify_token(token: str, secret: str) -> TokenPayload | None:
    """Convenience function to verify a JWT token.

    Args:
        token: The JWT token string.
        secret: Signing secret.

    Returns:
        TokenPayload if valid, None otherwise.
    """
    manager = JWTManager(secret)
    return manager.verify_token(token)
