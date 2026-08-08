"""API route definitions for personal-index."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from personal_index.models import IndexedPage, SearchResult

logger = logging.getLogger(__name__)


def register_routes(app, search_index=None, index_instance=None):
    """Register all API routes on the FastAPI app.

    Args:
        app: FastAPI application instance.
        search_index: Optional search index instance.
        index_instance: Optional index instance.
    """
    try:
        from fastapi import APIRouter, Query
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.warning("fastapi not installed, routes registered but non-functional")
        return

    router = APIRouter(prefix="/api/v1", tags=["personal-index"])

    @router.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "personal-index"}

    @router.get("/search")
    async def search(
        q: str = Query(..., min_length=1, description="Search query"),
        limit: int = Query(20, ge=1, le=100, description="Max results"),
        offset: int = Query(0, ge=0, description="Result offset"),
    ) -> Dict[str, Any]:
        """Search indexed pages."""
        results: List[Dict[str, Any]] = []
        total = 0
        if search_index:
            search_results = search_index.search(q, limit=limit, offset=offset)
            results = [r.to_dict() if hasattr(r, "to_dict") else r for r in search_results]
            total = len(results)
        return {
            "query": q,
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @router.get("/pages")
    async def list_pages(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        domain: Optional[str] = Query(None, description="Filter by domain"),
    ) -> Dict[str, Any]:
        """List indexed pages."""
        pages: List[Dict[str, Any]] = []
        if index_instance:
            all_pages = index_instance.get_all_pages()
            if domain:
                all_pages = [p for p in all_pages if p.domain == domain]
            paginated = all_pages[offset: offset + limit]
            pages = [p.to_dict() if hasattr(p, "to_dict") else p for p in paginated]
        return {
            "pages": pages,
            "total": len(pages),
            "limit": limit,
            "offset": offset,
        }

    @router.get("/pages/{page_id}")
    async def get_page(page_id: str) -> Dict[str, Any]:
        """Get a specific page by ID."""
        if index_instance:
            page = index_instance.get_page(page_id)
            if page:
                return {"page": page.to_dict() if hasattr(page, "to_dict") else page}
        return JSONResponse(status_code=404, content={"error": "Page not found"})

    @router.get("/stats")
    async def get_stats() -> Dict[str, Any]:
        """Get indexing statistics."""
        stats: Dict[str, Any] = {
            "total_pages": 0,
            "total_domains": 0,
            "total_interests": 0,
        }
        if index_instance:
            stats["total_pages"] = len(index_instance.get_all_pages())
            stats["total_domains"] = len(set(
                p.domain for p in index_instance.get_all_pages() if p.domain
            ))
        return stats

    @router.get("/interests")
    async def list_interests() -> Dict[str, Any]:
        """List configured interests."""
        interests: List[Dict[str, Any]] = []
        if index_instance:
            for interest in index_instance.interests:
                interests.append(interest.to_dict() if hasattr(interest, "to_dict") else interest)
        return {"interests": interests, "total": len(interests)}

    app.include_router(router)
    logger.info("API routes registered at /api/v1")
