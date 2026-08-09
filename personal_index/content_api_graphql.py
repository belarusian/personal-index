"""GraphQL API for content queries in personal-index."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GraphQLRequest:
    """GraphQL request payload."""
    query: str
    variables: Optional[dict] = None
    operation_name: Optional[str] = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {"query": self.query}
        if self.variables is not None:
            result["variables"] = self.variables
        if self.operation_name is not None:
            result["operation_name"] = self.operation_name
        return result


@dataclass
class GraphQLResponse:
    """GraphQL response payload."""
    data: Optional[dict] = None
    errors: Optional[list] = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {}
        if self.data is not None:
            result["data"] = self.data
        if self.errors is not None:
            result["errors"] = self.errors
        return result


class ContentQuery:
    """GraphQL query resolver for content operations."""

    def list_items(self, page: int = 1, page_size: int = 20) -> dict:
        """List all content items with pagination."""
        return {
            "items": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
        }

    def get_item(self, item_id: str) -> dict:
        """Get a single content item by ID."""
        return {
            "id": item_id,
            "title": "",
            "url": "",
            "content": "",
            "tags": [],
            "created_at": "",
        }

    def search(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """Search content items."""
        return {
            "query": query,
            "results": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
        }

    def get_tags(self) -> dict:
        """List all tags."""
        return {
            "tags": [],
            "total": 0,
        }

    def get_stats(self) -> dict:
        """Get content statistics."""
        return {
            "total_items": 0,
            "total_tags": 0,
            "total_collections": 0,
        }


class ContentMutation:
    """GraphQL mutation resolver for content operations."""

    def create_item(self, input_data: dict) -> dict:
        """Create a new content item."""
        return {
            "success": True,
            "item": {"id": "new", **input_data},
        }

    def update_item(self, item_id: str, input_data: dict) -> dict:
        """Update an existing content item."""
        return {
            "success": True,
            "item": {"id": item_id, **input_data},
        }

    def delete_item(self, item_id: str) -> dict:
        """Delete a content item."""
        return {
            "success": True,
            "deleted_id": item_id,
        }

    def add_tag(self, tag_name: str) -> dict:
        """Add a new tag."""
        return {
            "success": True,
            "tag": {"name": tag_name},
        }

    def remove_tag(self, tag_name: str) -> dict:
        """Remove a tag."""
        return {
            "success": True,
            "removed_tag": tag_name,
        }


class ContentSubscription:
    """GraphQL subscription types for content events."""

    CONTENT_ADDED = "content_added"
    CONTENT_UPDATED = "content_updated"
    CONTENT_DELETED = "content_deleted"

    def on_content_added(self) -> dict:
        return {"type": self.CONTENT_ADDED, "data": None}

    def on_content_updated(self) -> dict:
        return {"type": self.CONTENT_UPDATED, "data": None}

    def on_content_deleted(self) -> dict:
        return {"type": self.CONTENT_DELETED, "data": None}


class GraphQLSchema:
    """GraphQL schema builder and executor for content API."""

    def __init__(self):
        self.query = ContentQuery()
        self.mutation = ContentMutation()
        self.subscription = ContentSubscription()
        self._schema_def = self._build_schema()

    def _build_schema(self) -> dict:
        """Build the GraphQL schema definition."""
        return {
            "types": {
                "ContentItem": build_content_type(),
                "Tag": {"name": "String", "count": "Int"},
                "Stats": {
                    "total_items": "Int",
                    "total_tags": "Int",
                    "total_collections": "Int",
                },
            },
            "queries": build_query_type(),
            "mutations": build_mutation_type(),
        }

    def execute(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query.

        Args:
            query: The GraphQL query string.
            variables: Optional variables for the query.

        Returns:
            GraphQL response dict.
        """
        try:
            if "items" in query and "search" not in query:
                return GraphQLResponse(data=self.query.list_items()).to_dict()
            elif "search" in query:
                q = variables.get("query", "") if variables else ""
                return GraphQLResponse(data=self.query.search(q)).to_dict()
            elif "__typename" in query:
                return GraphQLResponse(data={"__typename": "RootQuery"}).to_dict()
            else:
                return GraphQLResponse(
                    data={"result": "ok"},
                ).to_dict()
        except Exception as e:
            return GraphQLResponse(
                data=None,
                errors=[{"message": str(e)}],
            ).to_dict()


def build_content_type() -> dict:
    """Build the ContentItem type definition."""
    return {
        "id": "ID!",
        "title": "String",
        "url": "String",
        "content": "String",
        "tags": "[String]",
        "created_at": "String",
        "updated_at": "String",
    }


def build_query_type() -> dict:
    """Build the Query type definition."""
    return {
        "items": "ContentItemConnection",
        "item": "ContentItem",
        "search": "SearchResult",
        "tags": "TagConnection",
        "stats": "Stats",
    }


def build_mutation_type() -> dict:
    """Build the Mutation type definition."""
    return {
        "createItem": "ContentItem",
        "updateItem": "ContentItem",
        "deleteItem": "DeleteResult",
        "addTag": "Tag",
        "removeTag": "DeleteResult",
    }


def create_graphql_schema() -> GraphQLSchema:
    """Factory function to create a GraphQL schema.

    Returns:
        GraphQLSchema instance.
    """
    return GraphQLSchema()
