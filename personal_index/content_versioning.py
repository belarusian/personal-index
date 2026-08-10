"""Content versioning functionality for personal index.

Provides functions to track and manage versions of content items.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ContentVersion:
    """A version of a content item."""

    version_id: str
    content: str
    created_at: str = ""
    author: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        """Set default timestamp."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class ContentVersioning:
    """Manage versions of content items."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        """Initialize the content versioning system.

        Args:
            storage_path: Path to store version data.
        """
        self.storage_path = storage_path or str(
            Path.home() / ".personal_index" / "versions.json"
        )
        self._versions: Dict[str, List[ContentVersion]] = {}
        self._load()

    def _load(self) -> None:
        """Load versions from storage."""
        if not os.path.exists(self.storage_path):
            self._versions = {}
            return
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            self._versions = {}
            for item_id, version_list in data.items():
                self._versions[item_id] = [
                    ContentVersion(
                        version_id=v["version_id"],
                        content=v["content"],
                        created_at=v.get("created_at", ""),
                        author=v.get("author", ""),
                        message=v.get("message", ""),
                    )
                    for v in version_list
                ]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._versions = {}

    def _save(self) -> None:
        """Save versions to storage."""
        parent = Path(self.storage_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for item_id, version_list in self._versions.items():
            data[item_id] = [
                {
                    "version_id": v.version_id,
                    "content": v.content,
                    "created_at": v.created_at,
                    "author": v.author,
                    "message": v.message,
                }
                for v in version_list
            ]
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def create_version(
        self, item_id: str, content: str, author: str = "", message: str = ""
    ) -> ContentVersion:
        """Create a new version of an item.

        Args:
            item_id: ID of the item to version.
            content: Content to store in this version.
            author: Optional author name.
            message: Optional commit message.

        Returns:
            The created ContentVersion object.
        """
        version_id = f"{item_id}_v{len(self._versions.get(item_id, [])) + 1}"
        version = ContentVersion(
            version_id=version_id,
            content=content,
            author=author,
            message=message,
        )
        
        if item_id not in self._versions:
            self._versions[item_id] = []
        self._versions[item_id].append(version)
        self._save()
        return version

    def get_versions(self, item_id: str) -> List[ContentVersion]:
        """Get all versions of an item.

        Args:
            item_id: ID of the item.

        Returns:
            List of ContentVersion objects.
        """
        return self._versions.get(item_id, [])

    def get_version(self, item_id: str, version_id: str) -> Optional[ContentVersion]:
        """Get a specific version of an item.

        Args:
            item_id: ID of the item.
            version_id: ID of the version.

        Returns:
            ContentVersion if found, None otherwise.
        """
        versions = self._versions.get(item_id, [])
        for v in versions:
            if v.version_id == version_id:
                return v
        return None

    def delete_version(self, item_id: str, version_id: str) -> bool:
        """Delete a specific version.

        Args:
            item_id: ID of the item.
            version_id: ID of the version to delete.

        Returns:
            True if deleted, False if not found.
        """
        if item_id in self._versions:
            original_len = len(self._versions[item_id])
            self._versions[item_id] = [
                v for v in self._versions[item_id] if v.version_id != version_id
            ]
            if len(self._versions[item_id]) < original_len:
                self._save()
                return True
        return False

    def clear_versions(self, item_id: str) -> bool:
        """Clear all versions of an item.

        Args:
            item_id: ID of the item.

        Returns:
            True if cleared.
        """
        if item_id in self._versions:
            del self._versions[item_id]
            self._save()
            return True
        return False


# Module-level instance for convenience
_default_versioning: Optional[ContentVersioning] = None


def _get_default_versioning() -> ContentVersioning:
    """Get or create the default versioning instance."""
    global _default_versioning
    if _default_versioning is None:
        _default_versioning = ContentVersioning()
    return _default_versioning


def create_version(item_id: str, content: str, author: str = "", message: str = "") -> ContentVersion:
    """Create a new version using the default versioning instance.

    Args:
        item_id: ID of the item to version.
        content: Content to store in this version.
        author: Optional author name.
        message: Optional commit message.

    Returns:
        The created ContentVersion object.
    """
    return _get_default_versioning().create_version(item_id, content, author, message)


def get_versions(item_id: str) -> List[ContentVersion]:
    """Get all versions of an item using the default versioning instance.

    Args:
        item_id: ID of the item.

    Returns:
        List of ContentVersion objects.
    """
    return _get_default_versioning().get_versions(item_id)
