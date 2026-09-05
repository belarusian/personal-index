"""Content collections module - group saved items into collections."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Collection:
    """A collection of saved content items."""

    name: str
    collection_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    item_ids: list[str] = field(default_factory=list)
    is_public: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str | None = None

    def add_item(self, item_id: str) -> None:
        """Add an item to this collection."""
        if item_id not in self.item_ids:
            self.item_ids.append(item_id)
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def remove_item(self, item_id: str) -> None:
        """Remove an item from this collection."""
        if item_id in self.item_ids:
            self.item_ids.remove(item_id)
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def contains(self, item_id: str) -> bool:
        """Check if an item is in this collection."""
        return item_id in self.item_ids

    def item_count(self) -> int:
        """Return the number of items in this collection."""
        return len(self.item_ids)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "collection_id": self.collection_id,
            "name": self.name,
            "description": self.description,
            "item_ids": list(self.item_ids),
            "is_public": self.is_public,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Collection:
        """Deserialize from dictionary."""
        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        return cls(
            collection_id=data.get("collection_id", uuid.uuid4().hex[:12]),
            name=data["name"],
            description=data.get("description", ""),
            item_ids=data.get("item_ids", []),
            is_public=data.get("is_public", False),
            created_at=created_at,
            updated_at=data.get("updated_at"),
        )


class CollectionManager:
    """Manages collections of saved content items."""

    def __init__(self) -> None:
        """Initialize the collection manager with empty storage."""
        self._collections: dict[str, Collection] = {}
        self._item_to_collections: dict[str, list[str]] = {}

    def create(
        self,
        name: str,
        description: str = "",
        is_public: bool = False,
    ) -> str:
        """Create a new collection. Returns the collection ID."""
        c = Collection(name=name, description=description, is_public=is_public)
        self._collections[c.collection_id] = c
        return c.collection_id

    def get(self, collection_id: str) -> Collection | None:
        """Get a collection by ID."""
        return self._collections.get(collection_id)

    def list_all(self) -> list[Collection]:
        """List all collections."""
        return list(self._collections.values())

    def list_public(self) -> list[Collection]:
        """List all public collections."""
        return [c for c in self._collections.values() if c.is_public]

    def list_private(self) -> list[Collection]:
        """List all private collections."""
        return [c for c in self._collections.values() if not c.is_public]

    def get_items(self, collection_id: str) -> list[str]:
        """Get all item IDs in a collection."""
        c = self._collections.get(collection_id)
        return list(c.item_ids) if c else []

    def get_collections_for_item(self, item_id: str) -> list[Collection]:
        """Get all collections containing a specific item."""
        cids = self._item_to_collections.get(item_id, [])
        return [self._collections[cid] for cid in cids if cid in self._collections]

    def add_item(self, collection_id: str, item_id: str) -> bool:
        """Add an item to a collection.

        Guard path: if `collection_id` is not in `_collections`, returns
        False without touching `Collection.item_ids` or the
        `_item_to_collections` reverse index.

        On success (collection exists):
          1. `Collection.add_item(item_id)` appends `item_id` to the
             collection's `item_ids` (skipping if already present) and
             refreshes `updated_at`.
          2. The `_item_to_collections[item_id]` reverse index is created
             if absent and `collection_id` is appended to it if not already
             listed.
        Returns True on success, False on the guard path.
        """
        c = self._collections.get(collection_id)
        if c:
            c.add_item(item_id)
            if item_id not in self._item_to_collections:
                self._item_to_collections[item_id] = []
            if collection_id not in self._item_to_collections[item_id]:
                self._item_to_collections[item_id].append(collection_id)
            return True
        return False

    def add_items(self, collection_id: str, item_ids: list[str]) -> None:
        """Add multiple items to a collection."""
        for item_id in item_ids:
            self.add_item(collection_id, item_id)

    def remove_item(self, collection_id: str, item_id: str) -> bool:
        """Remove an item from a collection."""
        c = self._collections.get(collection_id)
        if c:
            c.remove_item(item_id)
            if item_id in self._item_to_collections:
                if collection_id in self._item_to_collections[item_id]:
                    self._item_to_collections[item_id].remove(collection_id)
                if not self._item_to_collections[item_id]:
                    del self._item_to_collections[item_id]
            return True
        return False

    def update_name(self, collection_id: str, new_name: str) -> bool:
        """Update the name of a collection."""
        c = self._collections.get(collection_id)
        if c:
            c.name = new_name
            c.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def update_description(self, collection_id: str, description: str) -> bool:
        """Update the description of a collection."""
        c = self._collections.get(collection_id)
        if c:
            c.description = description
            c.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def rename(self, collection_id: str, new_name: str) -> bool:
        """Rename a collection (alias for update_name)."""
        return self.update_name(collection_id, new_name)

    def toggle_public(self, collection_id: str) -> bool:
        """Toggle the public/private status of a collection."""
        c = self._collections.get(collection_id)
        if c:
            c.is_public = not c.is_public
            c.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def delete(self, collection_id: str) -> bool:
        """Delete a collection."""
        c = self._collections.pop(collection_id, None)
        if c:
            # Clean up item-to-collection index
            for item_id in c.item_ids:
                if item_id in self._item_to_collections:
                    self._item_to_collections[item_id] = [
                        cid for cid in self._item_to_collections[item_id]
                        if cid != collection_id
                    ]
                    if not self._item_to_collections[item_id]:
                        del self._item_to_collections[item_id]
            return True
        return False

    def clear_items(self, collection_id: str) -> bool:
        """Remove all items from a collection."""
        c = self._collections.get(collection_id)
        if c:
            for item_id in c.item_ids:
                if item_id in self._item_to_collections:
                    if collection_id in self._item_to_collections[item_id]:
                        self._item_to_collections[item_id].remove(collection_id)
                    if not self._item_to_collections[item_id]:
                        del self._item_to_collections[item_id]
            c.item_ids.clear()
            c.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def move_item(
        self, item_id: str, from_collection_id: str, to_collection_id: str
    ) -> bool:
        """Add the item to the destination collection and remove it from the
        source collection if present. Returns True iff both collections exist
        (the item does not need to be in the source); False if either collection
        is missing."""
        from_c = self._collections.get(from_collection_id)
        to_c = self._collections.get(to_collection_id)
        if from_c and to_c:
            from_c.remove_item(item_id)
            to_c.add_item(item_id)
            # Update index
            if item_id in self._item_to_collections:
                if from_collection_id in self._item_to_collections[item_id]:
                    self._item_to_collections[item_id].remove(from_collection_id)
                if not self._item_to_collections[item_id]:
                    del self._item_to_collections[item_id]
            if item_id not in self._item_to_collections:
                self._item_to_collections[item_id] = []
            if to_collection_id not in self._item_to_collections[item_id]:
                self._item_to_collections[item_id].append(to_collection_id)
            return True
        return False

    def merge(self, target_id: str, source_id: str) -> bool:
        """Merge source collection into target collection, deleting source."""
        target = self._collections.get(target_id)
        source = self._collections.get(source_id)
        if target and source:
            for item_id in source.item_ids:
                target.add_item(item_id)
                if item_id not in self._item_to_collections:
                    self._item_to_collections[item_id] = []
                if target_id not in self._item_to_collections[item_id]:
                    self._item_to_collections[item_id].append(target_id)
            # Delete source
            self.delete(source_id)
            return True
        return False

    def search(self, query: str) -> list[Collection]:
        """Search collections by name or description."""
        query_lower = query.lower()
        results = []
        for c in self._collections.values():
            if query_lower in c.name.lower() or query_lower in c.description.lower():
                results.append(c)
        return results

    def get_recent(self, limit: int = 10) -> list[Collection]:
        """Get the most recently created collections."""
        all_c = list(self._collections.values())
        all_c.sort(key=lambda c: c.created_at, reverse=True)
        return all_c[:limit]

    def count(self) -> int:
        """Return total number of collections."""
        return len(self._collections)

    def get_stats(self) -> dict:
        """Get collection statistics."""
        total_items = sum(len(c.item_ids) for c in self._collections.values())
        return {
            "total_collections": len(self._collections),
            "total_items": total_items,
            "public_collections": len(self.list_public()),
            "private_collections": len(self.list_private()),
        }

    def serialize(self) -> list[dict]:
        """Serialize all collections to a list of dicts."""
        return [c.to_dict() for c in self._collections.values()]

    def deserialize(self, data: list[dict]) -> None:
        """Deserialize collections from a list of dicts."""
        self._collections.clear()
        self._item_to_collections.clear()
        for item in data:
            c = Collection.from_dict(item)
            self._collections[c.collection_id] = c
            for item_id in c.item_ids:
                if item_id not in self._item_to_collections:
                    self._item_to_collections[item_id] = []
                if c.collection_id not in self._item_to_collections[item_id]:
                    self._item_to_collections[item_id].append(c.collection_id)
