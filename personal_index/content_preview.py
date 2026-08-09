"""Content preview module - generate preview thumbnails for saved content."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class PreviewType(str, Enum):
    """Type of preview to generate."""

    TEXT = "text"
    IMAGE = "image"
    CARD = "card"
    VIDEO = "video"


class PreviewStatus(str, Enum):
    """Status of a preview."""

    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


@dataclass
class Preview:
    """A preview/thumbnail for a saved URL."""

    url: str
    preview_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    preview_type: PreviewType = PreviewType.TEXT
    image_url: Optional[str] = None
    status: PreviewStatus = PreviewStatus.READY
    error: Optional[str] = None
    width: int = 0
    height: int = 0
    ttl_hours: int = 0  # 0 means no expiry
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def is_ready(self) -> bool:
        """Check if the preview is ready."""
        return self.status == PreviewStatus.READY

    def generate_text_preview(self, max_length: int = 200) -> str:
        """Generate a text preview from the description."""
        if not self.description:
            return ""
        if len(self.description) <= max_length:
            return self.description
        return self.description[:max_length] + "..."

    def get_favicon_url(self) -> str:
        """Generate a favicon URL from the page URL."""
        parsed = urlparse(self.url)
        return f"https://{parsed.hostname}/favicon.ico"

    def get_og_image(self) -> Optional[str]:
        """Get the Open Graph image URL."""
        return self.image_url

    def update_status(self, status: PreviewStatus) -> None:
        """Update the preview status."""
        self.status = status

    def update_error(self, error: str) -> None:
        """Update the preview error."""
        self.status = PreviewStatus.FAILED
        self.error = error

    def is_expired(self) -> bool:
        """Check if the preview has expired."""
        if self.ttl_hours == 0:
            return False
        try:
            created = datetime.fromisoformat(self.created_at)
            now = datetime.now(timezone.utc)
            elapsed = (now - created).total_seconds() / 3600
            return elapsed >= self.ttl_hours
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "preview_id": self.preview_id,
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "preview_type": self.preview_type.value,
            "image_url": self.image_url,
            "status": self.status.value,
            "error": self.error,
            "width": self.width,
            "height": self.height,
            "ttl_hours": self.ttl_hours,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Preview":
        """Deserialize from dictionary."""
        ptype = data.get("preview_type", "text")
        if isinstance(ptype, str):
            ptype = PreviewType(ptype)
        elif not isinstance(ptype, PreviewType):
            ptype = PreviewType.TEXT

        status = data.get("status", "ready")
        if isinstance(status, str):
            status = PreviewStatus(status)
        elif not isinstance(status, PreviewStatus):
            status = PreviewStatus.READY

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            preview_id=data.get("preview_id", uuid.uuid4().hex[:12]),
            url=data["url"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            preview_type=ptype,
            image_url=data.get("image_url"),
            status=status,
            error=data.get("error"),
            width=data.get("width", 0),
            height=data.get("height", 0),
            ttl_hours=data.get("ttl_hours", 0),
            created_at=created_at,
        )


class PreviewManager:
    """Manages preview thumbnails for saved content."""

    def __init__(self) -> None:
        self._previews: dict[str, Preview] = {}
        self._url_to_preview: dict[str, str] = {}

    def create_preview(
        self,
        url: str,
        title: str = "",
        description: str = "",
        preview_type: PreviewType = PreviewType.TEXT,
        image_url: Optional[str] = None,
        status: PreviewStatus = PreviewStatus.READY,
        error: Optional[str] = None,
        width: int = 0,
        height: int = 0,
        ttl_hours: int = 0,
        created_at: Optional[str] = None,
    ) -> str:
        """Create a new preview. Returns the preview ID."""
        preview = Preview(
            url=url,
            title=title,
            description=description,
            preview_type=preview_type,
            image_url=image_url,
            status=status,
            error=error,
            width=width,
            height=height,
            ttl_hours=ttl_hours,
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
        )
        self._previews[preview.preview_id] = preview
        self._url_to_preview[url] = preview.preview_id
        return preview.preview_id

    def get_preview(self, preview_id: str) -> Optional[Preview]:
        """Get a preview by ID."""
        return self._previews.get(preview_id)

    def get_preview_by_url(self, url: str) -> Optional[Preview]:
        """Get a preview by URL."""
        pid = self._url_to_preview.get(url)
        if pid:
            return self._previews.get(pid)
        return None

    def list_previews(
        self,
        preview_type: Optional[PreviewType] = None,
        status: Optional[PreviewStatus] = None,
        domain: Optional[str] = None,
    ) -> list[Preview]:
        """List previews with optional filters."""
        result = list(self._previews.values())
        if preview_type is not None:
            result = [p for p in result if p.preview_type == preview_type]
        if status is not None:
            result = [p for p in result if p.status == status]
        if domain is not None:
            result = [
                p for p in result
                if urlparse(p.url).hostname == domain
            ]
        return result

    def update_preview(
        self,
        preview_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        preview_type: Optional[PreviewType] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        """Update a preview's properties."""
        preview = self._previews.get(preview_id)
        if not preview:
            return
        if title is not None:
            preview.title = title
        if description is not None:
            preview.description = description
        if image_url is not None:
            preview.image_url = image_url
        if preview_type is not None:
            preview.preview_type = preview_type
        if width is not None:
            preview.width = width
        if height is not None:
            preview.height = height

    def delete_preview(self, preview_id: str) -> bool:
        """Delete a preview. Returns True if deleted."""
        preview = self._previews.pop(preview_id, None)
        if preview:
            self._url_to_preview.pop(preview.url, None)
            return True
        return False

    def get_preview_count(self) -> int:
        """Get total number of previews."""
        return len(self._previews)

    def get_pending_previews(self) -> list[Preview]:
        """Get all pending previews."""
        return [p for p in self._previews.values() if p.status == PreviewStatus.PENDING]

    def get_expired_previews(self) -> list[Preview]:
        """Get all expired previews."""
        return [p for p in self._previews.values() if p.is_expired()]

    def generate_text_preview(
        self, preview_id: str, max_length: int = 200
    ) -> str:
        """Generate a text preview for a preview."""
        preview = self._previews.get(preview_id)
        if not preview:
            return ""
        return preview.generate_text_preview(max_length)

    def generate_batch_previews(self, urls: list[str]) -> list[str]:
        """Generate previews for multiple URLs. Returns preview IDs."""
        ids = []
        for url in urls:
            pid = self.create_preview(url, status=PreviewStatus.PENDING)
            ids.append(pid)
        return ids

    def mark_preview_ready(
        self,
        preview_id: str,
        image_url: Optional[str] = None,
        width: int = 0,
        height: int = 0,
    ) -> None:
        """Mark a preview as ready."""
        preview = self._previews.get(preview_id)
        if preview:
            preview.status = PreviewStatus.READY
            if image_url:
                preview.image_url = image_url
            if width:
                preview.width = width
            if height:
                preview.height = height

    def mark_preview_failed(self, preview_id: str, error: str) -> None:
        """Mark a preview as failed."""
        preview = self._previews.get(preview_id)
        if preview:
            preview.update_error(error)

    def refresh_preview(self, preview_id: str) -> str:
        """Refresh a preview. Returns the new preview ID."""
        old = self._previews.get(preview_id)
        if not old:
            return self.create_preview("", status=PreviewStatus.PENDING)
        new_id = self.create_preview(
            old.url,
            status=PreviewStatus.PENDING,
        )
        return new_id

    def cleanup_expired(self) -> int:
        """Remove expired previews. Returns count removed."""
        expired = self.get_expired_previews()
        for p in expired:
            self.delete_preview(p.preview_id)
        return len(expired)

    def get_previews_for_urls(self, urls: list[str]) -> list[Preview]:
        """Get previews for a list of URLs."""
        result = []
        for url in urls:
            preview = self.get_preview_by_url(url)
            if preview:
                result.append(preview)
        return result

    def get_preview_summary(self) -> dict:
        """Get a summary of preview statuses."""
        summary = {
            "total": len(self._previews),
            "ready": 0,
            "pending": 0,
            "failed": 0,
        }
        for p in self._previews.values():
            if p.status == PreviewStatus.READY:
                summary["ready"] += 1
            elif p.status == PreviewStatus.PENDING:
                summary["pending"] += 1
            elif p.status == PreviewStatus.FAILED:
                summary["failed"] += 1
        return summary

    def to_dict(self) -> dict:
        """Serialize the manager state."""
        return {
            "previews": {
                pid: p.to_dict() for pid, p in self._previews.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreviewManager":
        """Deserialize manager state."""
        mgr = cls()
        for pid, pdata in data.get("previews", {}).items():
            preview = Preview.from_dict(pdata)
            mgr._previews[pid] = preview
            mgr._url_to_preview[preview.url] = pid
        return mgr
