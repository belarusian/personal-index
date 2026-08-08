"""API key management for personal-index authentication."""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class APIKey:
    """Represents an API key with metadata."""
    key_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    hashed_key: str = ""
    prefix: str = "pk_"
    owner: str = ""
    permissions: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    usage_count: int = 0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "name": self.name,
            "prefix": self.prefix,
            "owner": self.owner,
            "permissions": self.permissions,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_used_at": self.last_used_at,
            "usage_count": self.usage_count,
            "is_active": self.is_active,
        }


class APIKeyStore:
    """In-memory store for API keys with CRUD operations."""

    def __init__(self):
        self._keys: Dict[str, APIKey] = {}
        self._key_lookup: Dict[str, str] = {}  # hashed_key -> key_id

    def create_key(
        self,
        owner: str,
        name: str = "",
        permissions: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
        prefix: str = "pk_",
    ) -> tuple[str, APIKey]:
        """Create a new API key.

        Args:
            owner: Key owner identifier.
            name: Human-readable name.
            permissions: List of permission strings.
            expires_at: ISO format expiration datetime.
            prefix: Key prefix for identification.

        Returns:
            Tuple of (raw_key, APIKey metadata).
        """
        raw_key = prefix + secrets.token_urlsafe(32)
        hashed = self._hash_key(raw_key)
        api_key = APIKey(
            name=name,
            hashed_key=hashed,
            prefix=prefix,
            owner=owner,
            permissions=permissions or [],
            expires_at=expires_at,
        )
        self._keys[api_key.key_id] = api_key
        self._key_lookup[hashed] = api_key.key_id
        return raw_key, api_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return its metadata if valid.

        Args:
            raw_key: The raw API key string.

        Returns:
            APIKey if valid, None otherwise.
        """
        hashed = self._hash_key(raw_key)
        key_id = self._key_lookup.get(hashed)
        if not key_id:
            return None
        api_key = self._keys.get(key_id)
        if not api_key:
            return None
        if not api_key.is_active:
            return None
        if api_key.expires_at:
            try:
                exp = datetime.fromisoformat(api_key.expires_at)
                if exp < datetime.now(timezone.utc):
                    return None
            except ValueError:
                pass
        # Update usage
        api_key.last_used_at = datetime.now(timezone.utc).isoformat()
        api_key.usage_count += 1
        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            key_id: The key ID to revoke.

        Returns:
            True if key was revoked, False if not found.
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return False
        api_key.is_active = False
        self._key_lookup.pop(api_key.hashed_key, None)
        return True

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get API key metadata by ID.

        Args:
            key_id: The key ID.

        Returns:
            APIKey if found, None otherwise.
        """
        return self._keys.get(key_id)

    def list_keys(self, owner: Optional[str] = None) -> List[APIKey]:
        """List API keys, optionally filtered by owner.

        Args:
            owner: Filter by owner identifier.

        Returns:
            List of APIKey objects.
        """
        keys = list(self._keys.values())
        if owner:
            keys = [k for k in keys if k.owner == owner]
        return keys

    def delete_key(self, key_id: str) -> bool:
        """Permanently delete an API key.

        Args:
            key_id: The key ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        api_key = self._keys.pop(key_id, None)
        if api_key:
            self._key_lookup.pop(api_key.hashed_key, None)
            return True
        return False

    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def validate_api_key(store: APIKeyStore, raw_key: str) -> Optional[APIKey]:
    """Convenience function to validate an API key.

    Args:
        store: The API key store.
        raw_key: The raw API key string.

    Returns:
        APIKey if valid, None otherwise.
    """
    return store.validate_key(raw_key)
