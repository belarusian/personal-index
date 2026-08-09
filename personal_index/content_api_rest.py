"""REST API for content operations in personal-index."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

try:
    from fastapi import FastAPI, APIRouter, Query, HTTPException
    from fastapi.responses import JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@dataclass
class ContentResponse:
    """Standard response wrapper for content API."""
    success: bool = True
    data: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


@dataclass
class ErrorResponse:
    """Error response with code and optional details."""
    message: str
    code: int = 400
    details: Optional[list] = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "error": self.message,
            "code": self.code,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class PaginatedResponse:
    """Paginated response for list endpoints."""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int = field(init=False)

    def __post_init__(self):
        self.total_pages = max(1, math.ceil(self.total / self.page_size))

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }


@dataclass
class ContentListResponse:
    """Response for content list operations."""
    items: list
    total: int = 0

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "total": self.total,
        }


class ContentRouter:
    """FastAPI-based REST router for content operations."""

    def __init__(self, prefix: str = "/api/v1/content"):
        if HAS_FASTAPI:
            self.app = FastAPI(title="Personal Index Content API", version="1.0.0")
            self.router = APIRouter(prefix=prefix, tags=["content"])
            self._register_routes()
            self.app.include_router(self.router)
        else:
            self.app = None  # type: ignore[assignment]

    def _register_routes(self):
        """Register all content API routes."""
        @self.router.get("/health")
        async def health_check():
            return {"status": "ok", "service": "content-api"}

        @self.router.get("/items")
        async def list_items(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            q: Optional[str] = Query(None),
            tag: Optional[str] = Query(None),
        ):
            return ContentResponse(
                data=PaginatedResponse(
                    items=[], total=0, page=page, page_size=page_size
                ).to_dict()
            ).to_dict()

        @self.router.get("/items/{item_id}")
        async def get_item(item_id: str):
            return ContentResponse(
                success=False,
                error=f"Item {item_id} not found",
            ).to_dict()

        @self.router.post("/items")
        async def create_item(item: dict):
            return ContentResponse(
                data={"id": "new_item", **item},
            ).to_dict()

        @self.router.put("/items/{item_id}")
        async def update_item(item_id: str, item: dict):
            return ContentResponse(
                data={"id": item_id, **item},
            ).to_dict()

        @self.router.delete("/items/{item_id}")
        async def delete_item(item_id: str):
            return ContentResponse(
                data={"deleted": item_id},
            ).to_dict()

        @self.router.get("/search")
        async def search_content(
            q: str = Query(..., min_length=1),
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
        ):
            return ContentResponse(
                data=PaginatedResponse(
                    items=[], total=0, page=page, page_size=page_size
                ).to_dict()
            ).to_dict()

        @self.router.get("/tags")
        async def list_tags():
            return ContentListResponse(items=[], total=0).to_dict()

        @self.router.get("/stats")
        async def get_stats():
            return ContentResponse(
                data={
                    "total_items": 0,
                    "total_tags": 0,
                    "total_collections": 0,
                }
            ).to_dict()


def create_router(prefix: str = "/api/v1/content") -> Any:
    """Factory function to create a content API router.

    Args:
        prefix: URL prefix for all routes.

    Returns:
        FastAPI app or APIRouter instance.
    """
    router = ContentRouter(prefix=prefix)
    return router.app if HAS_FASTAPI else router
