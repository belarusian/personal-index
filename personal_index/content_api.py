"""
Content API Module
REST API endpoints for content operations.
Uses a lightweight approach compatible with any WSGI/ASGI framework.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


class ContentAPI:
    """REST API handler for content operations."""

    def __init__(self, storage: Optional[Dict[str, Any]] = None):
        self._store: Dict[str, Dict[str, Any]] = storage or {}
        self._next_id = 1

    def handle_request(
        self, method: str, path: str, body: Optional[str] = None,
        query_string: str = ""
    ) -> Tuple[int, Dict[str, Any]]:
        """Route and handle an HTTP request."""
        parsed = urlparse(path)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        params = parse_qs(query_string)

        # Route: /api/v1/health
        if path_parts == ["api", "v1", "health"]:
            return self._health_check()

        # Route: /api/v1/stats
        if path_parts == ["api", "v1", "stats"]:
            return self._get_stats()

        # Route: /api/v1/content
        if path_parts == ["api", "v1", "content"]:
            if method == "GET":
                return self._list_content(params)
            elif method == "POST":
                return self._create_content(body)

        # Route: /api/v1/content/search
        if path_parts == ["api", "v1", "content", "search"]:
            if method == "GET":
                return self._search_content(params)

        # Route: /api/v1/content/export
        if path_parts == ["api", "v1", "content", "export"]:
            if method == "GET":
                return self._export_content(params)

        # Route: /api/v1/content/{id}
        if len(path_parts) == 4 and path_parts[:3] == ["api", "v1", "content"]:
            item_id = path_parts[3]
            if method == "GET":
                return self._get_content(item_id)
            elif method == "PUT":
                return self._update_content(item_id, body)
            elif method == "DELETE":
                return self._delete_content(item_id)

        return 404, {"error": "Not found", "path": path}

    def _list_content(self, params: Dict[str, List[str]]) -> Tuple[int, Dict[str, Any]]:
        items = list(self._store.values())
        # Pagination
        page = int(params.get("page", ["1"])[0])
        per_page = int(params.get("per_page", ["20"])[0])
        per_page = min(per_page, 100)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = items[start:end]
        return 200, {
            "items": paginated,
            "total": len(items),
            "page": page,
            "per_page": per_page,
        }

    def _get_content(self, item_id: str) -> Tuple[int, Dict[str, Any]]:
        item = self._store.get(item_id)
        if item is None:
            return 404, {"error": f"Content item '{item_id}' not found"}
        return 200, {"item": item}

    def _create_content(self, body: Optional[str]) -> Tuple[int, Dict[str, Any]]:
        if not body:
            return 400, {"error": "Request body is required"}
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return 400, {"error": "Invalid JSON in request body"}
        if not isinstance(data, dict):
            return 400, {"error": "Request body must be a JSON object"}
        item_id = str(self._next_id)
        self._next_id += 1
        item = {
            "id": item_id,
            "title": data.get("title", "Untitled"),
            "description": data.get("description", ""),
            "link": data.get("link", ""),
            "tags": data.get("tags", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store[item_id] = item
        return 201, {"item": item}

    def _update_content(self, item_id: str, body: Optional[str]) -> Tuple[int, Dict[str, Any]]:
        if item_id not in self._store:
            return 404, {"error": f"Content item '{item_id}' not found"}
        if not body:
            return 400, {"error": "Request body is required"}
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return 400, {"error": "Invalid JSON in request body"}
        item = self._store[item_id]
        for key in ("title", "description", "link", "tags"):
            if key in data:
                item[key] = data[key]
        item["updated_at"] = datetime.now(timezone.utc).isoformat()
        return 200, {"item": item}

    def _delete_content(self, item_id: str) -> Tuple[int, Dict[str, Any]]:
        if item_id not in self._store:
            return 404, {"error": f"Content item '{item_id}' not found"}
        deleted = self._store.pop(item_id)
        return 200, {"deleted": True, "id": item_id}

    def _search_content(self, params: Dict[str, List[str]]) -> Tuple[int, Dict[str, Any]]:
        q = params.get("q", [""])[0]
        if not q:
            return 400, {"error": "Search query parameter 'q' is required"}
        results = []
        q_lower = q.lower()
        for item in self._store.values():
            text = f"{item.get('title', '')} {item.get('description', '')}".lower()
            if q_lower in text:
                results.append(item)
        return 200, {"results": results, "total": len(results), "query": q}

    def _export_content(self, params: Dict[str, List[str]]) -> Tuple[int, Dict[str, Any]]:
        fmt = params.get("format", ["json"])[0]
        items = list(self._store.values())
        return 200, {"format": fmt, "items": items, "total": len(items)}

    def _health_check(self) -> Tuple[int, Dict[str, Any]]:
        return 200, {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

    def _get_stats(self) -> Tuple[int, Dict[str, Any]]:
        return 200, {
            "total_items": len(self._store),
            "tags": self._collect_tags(),
        }

    def _collect_tags(self) -> Dict[str, int]:
        tag_counts: Dict[str, int] = {}
        for item in self._store.values():
            for tag in item.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return tag_counts
    def _validate_content(self, data):
        """Validate content data and return errors."""
        errors = []
        if not isinstance(data, dict):
            return ["Request body must be a JSON object"]
        if "title" in data:
            if not isinstance(data["title"], str):
                errors.append("Title must be a string")
            elif len(data["title"]) > 200:
                errors.append("Title must be under 200 characters")
        if "tags" in data and not isinstance(data["tags"], list):
            errors.append("Tags must be a list")
        return errors





class RequestLogger:
    """Middleware that logs API requests."""

    def __init__(self, api):
        self.api = api
        self._log = []

    def handle_request(self, method, path, body=None, query_string=""):
        entry = {
            "method": method,
            "path": path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        status, response = self.api.handle_request(method, path, body, query_string)
        entry["status"] = status
        self._log.append(entry)
        return status, response

    @property
    def log(self):
        return list(self._log)

    def clear_log(self):
        self._log.clear()
