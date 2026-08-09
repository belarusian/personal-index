"""Content sharing module - generate shareable links for saved items."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional


class ShareFormat(str, Enum):
    """Formats for sharing content."""

    URL = "url"
    QR_CODE = "qr_code"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class ShareLink:
    """A shareable link for a content item."""

    content_id: str
    token: str
    share_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    view_count: int = 0
    max_views: Optional[int] = None
    is_active: bool = True
    expires_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __repr__(self) -> str:
        return f"ShareLink(content_id={self.content_id!r}, token={self.token!r})"

    def is_expired(self) -> bool:
        """Check if the share link has expired."""
        if not self.expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > expiry
        except ValueError:
            return False

    def deactivate(self) -> None:
        """Deactivate the share link."""
        self.is_active = False

    def increment_views(self) -> None:
        """Increment the view count."""
        self.view_count += 1

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "share_id": self.share_id,
            "content_id": self.content_id,
            "token": self.token,
            "view_count": self.view_count,
            "max_views": self.max_views,
            "is_active": self.is_active,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShareLink":
        """Deserialize from dictionary."""
        return cls(
            share_id=data.get("share_id", uuid.uuid4().hex[:12]),
            content_id=data["content_id"],
            token=data["token"],
            view_count=data.get("view_count", 0),
            max_views=data.get("max_views"),
            is_active=data.get("is_active", True),
            expires_at=data.get("expires_at"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ShareResult:
    """Result of generating a share link."""

    share_id: str
    token: str
    url: str
    format: ShareFormat
    content: str
    expires_at: Optional[str] = None
    max_views: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "share_id": self.share_id,
            "token": self.token,
            "url": self.url,
            "format": self.format.value,
            "content": self.content,
            "expires_at": self.expires_at,
            "max_views": self.max_views,
        }


class ShareStore:
    """Manages shareable links for content items."""

    def __init__(self, base_url: str = "https://example.com/s") -> None:
        self._base_url = base_url.rstrip("/")
        self._links: Dict[str, ShareLink] = {}
        self._by_content: Dict[str, List[str]] = {}

    def create_share_link(
        self,
        content_id: str,
        expires_at: Optional[datetime] = None,
        max_views: Optional[int] = None,
    ) -> ShareLink:
        """Create a new shareable link for a content item."""
        token = uuid.uuid4().hex[:16]
        link = ShareLink(
            content_id=content_id,
            token=token,
            max_views=max_views,
            expires_at=expires_at.isoformat() if expires_at else None,
        )
        self._links[token] = link
        if content_id not in self._by_content:
            self._by_content[content_id] = []
        self._by_content[content_id].append(token)
        return link

    def get_by_token(self, token: str) -> Optional[ShareLink]:
        """Get a share link by its token."""
        return self._links.get(token)

    def get_share_url(self, token: str) -> str:
        """Get the full share URL for a token."""
        return f"{self._base_url}/{token}"

    def list_share_links(self) -> List[ShareLink]:
        """List all share links."""
        return list(self._links.values())

    def list_for_content(self, content_id: str) -> List[ShareLink]:
        """List all share links for a specific content item."""
        tokens = self._by_content.get(content_id, [])
        return [self._links[t] for t in tokens if t in self._links]

    def deactivate(self, token: str) -> bool:
        """Deactivate a share link."""
        link = self._links.get(token)
        if link:
            link.deactivate()
            return True
        return False

    def delete(self, token: str) -> bool:
        """Delete a share link."""
        if token not in self._links:
            return False
        link = self._links.pop(token)
        content_id = link.content_id
        if content_id in self._by_content:
            self._by_content[content_id] = [
                t for t in self._by_content[content_id] if t != token
            ]
        return True

    def track_view(self, token: str) -> bool:
        """Track a view of a share link. Returns True if view was tracked."""
        link = self._links.get(token)
        if not link:
            return False
        if not link.is_active:
            return False
        if link.is_expired():
            return False
        link.increment_views()
        # Check if max views reached
        if link.max_views and link.view_count >= link.max_views:
            link.deactivate()
        return True

    def generate_share(
        self, token: str, fmt: ShareFormat
    ) -> Optional[ShareResult]:
        """Generate a share result in the specified format."""
        link = self._links.get(token)
        if not link:
            return None
        if not link.is_active:
            return None
        if link.is_expired():
            return None

        url = self.get_share_url(token)

        if fmt == ShareFormat.URL:
            content = url
        elif fmt == ShareFormat.MARKDOWN:
            content = f"[Shared content]({url})"
        elif fmt == ShareFormat.HTML:
            content = f'<a href="{url}">Shared content</a>'
        elif fmt == ShareFormat.QR_CODE:
            # QR code as a data URI placeholder
            content = f"QR_CODE:{url}"
        else:
            content = url

        return ShareResult(
            share_id=link.share_id,
            token=token,
            url=url,
            format=fmt,
            content=content,
            expires_at=link.expires_at,
            max_views=link.max_views,
        )

    def get_stats(self) -> dict:
        """Get sharing statistics."""
        total = len(self._links)
        active = sum(1 for l in self._links.values() if l.is_active and not l.is_expired())
        total_views = sum(l.view_count for l in self._links.values())
        return {
            "total_links": total,
            "active_links": active,
            "total_views": total_views,
        }

    def clear(self) -> None:
        """Remove all share links."""
        self._links.clear()
        self._by_content.clear()

    def serialize(self) -> List[dict]:
        """Serialize all share links."""
        return [link.to_dict() for link in self._links.values()]

    def deserialize(self, data: List[dict]) -> None:
        """Deserialize share links."""
        self.clear()
        for item in data:
            link = ShareLink.from_dict(item)
            self._links[link.token] = link
            if link.content_id not in self._by_content:
                self._by_content[link.content_id] = []
            self._by_content[link.content_id].append(link.token)
