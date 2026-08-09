"""Content API keys - manage API keys for external services."""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class APIKeyScope(str, Enum):
    """Scopes/permissions for API keys."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    CRAWL = "crawl"
    INDEX = "index"


class APIKeyStatus(str, Enum):
    """Status of an API key."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


@dataclass
class APIKeyUsage:
    """Records a single API key usage event."""
    key_id: str
    endpoint: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status_code: int = 200
    user_agent: str = ""

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


@dataclass
class APIKeyValidationResult:
    """Result of validating an API key."""
    is_valid: bool
    key: Optional[APIKeyEntry] = None
    error: str = ""


@dataclass
class APIKeyEntry:
    """Represents an API key entry."""
    name: str
    owner: str
    key_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    scopes: list[APIKeyScope] = field(default_factory=lambda: [APIKeyScope.READ])
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    expires_at: Optional[datetime] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_used_at: Optional[str] = None
    usage_count: int = 0
    usage_history: list[APIKeyUsage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self) -> bool:
        """Check if the key is valid for use."""
        if self.status != APIKeyStatus.ACTIVE:
            return False
        if self.is_expired():
            return False
        return True

    def has_scope(self, scope: APIKeyScope) -> bool:
        """Check if the key has a specific scope."""
        return scope in self.scopes

    def revoke(self) -> None:
        """Revoke this key."""
        self.status = APIKeyStatus.REVOKED

    def suspend(self) -> None:
        """Suspend this key."""
        self.status = APIKeyStatus.SUSPENDED

    def activate(self) -> None:
        """Activate this key."""
        self.status = APIKeyStatus.ACTIVE

    def record_usage(self, usage: APIKeyUsage) -> None:
        """Record a usage event."""
        self.usage_history.append(usage)
        self.usage_count += 1
        self.last_used_at = usage.timestamp

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


class APIKeyStore:
    """Manages API keys for external services."""

    def __init__(self):
        self._keys: dict[str, APIKeyEntry] = {}

    def create_key(
        self,
        name: str,
        owner: str,
        scopes: Optional[list[APIKeyScope]] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> APIKeyEntry:
        """Create a new API key."""
        if scopes is None:
            scopes = [APIKeyScope.READ]

        key = APIKeyEntry(
            name=name,
            owner=owner,
            scopes=scopes,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self._keys[key.key_id] = key
        return key

    def get_key(self, key_id: str) -> Optional[APIKeyEntry]:
        """Get a key by ID."""
        return self._keys.get(key_id)

    def list_keys(
        self,
        owner: Optional[str] = None,
        status: Optional[APIKeyStatus] = None,
    ) -> list[APIKeyEntry]:
        """List keys with optional filtering."""
        keys = list(self._keys.values())
        if owner:
            keys = [k for k in keys if k.owner == owner]
        if status:
            keys = [k for k in keys if k.status == status]
        return keys

    def revoke_key(self, key_id: str) -> bool:
        """Revoke a key."""
        key = self._keys.get(key_id)
        if key:
            key.revoke()
            return True
        return False

    def delete_key(self, key_id: str) -> bool:
        """Delete a key permanently."""
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False

    def validate_key(
        self,
        key_id: str,
        required_scope: APIKeyScope,
    ) -> APIKeyValidationResult:
        """Validate a key for a specific scope."""
        key = self._keys.get(key_id)
        if key is None:
            return APIKeyValidationResult(
                is_valid=False,
                error="Key not found",
            )
        if not key.is_valid():
            error = "Key is revoked" if key.status != APIKeyStatus.ACTIVE else "Key is expired"
            return APIKeyValidationResult(
                is_valid=False,
                key=key,
                error=error,
            )
        if not key.has_scope(required_scope):
            return APIKeyValidationResult(
                is_valid=False,
                key=key,
                error=f"Missing scope: {required_scope.value}",
            )
        return APIKeyValidationResult(is_valid=True, key=key)

    def record_usage(self, key_id: str, endpoint: str) -> Optional[APIKeyUsage]:
        """Record a usage event for a key."""
        key = self._keys.get(key_id)
        if key is None:
            return None
        usage = APIKeyUsage(key_id=key_id, endpoint=endpoint)
        key.record_usage(usage)
        return usage

    def get_usage_history(self, key_id: str) -> list[APIKeyUsage]:
        """Get usage history for a key."""
        key = self._keys.get(key_id)
        if key is None:
            return []
        return list(key.usage_history)

    @property
    def key_count(self) -> int:
        return len(self._keys)

    @property
    def active_key_count(self) -> int:
        return sum(1 for k in self._keys.values() if k.status == APIKeyStatus.ACTIVE)
