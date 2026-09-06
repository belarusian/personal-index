"""
Content API Module
REST API endpoints for content operations.
Exposes a lightweight request/response interface
(`handle_request(method, path, body, query_string) -> (status, payload)`)
that callers can adapt to their own HTTP framework.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse


class ContentAPI:
    """REST API handler for content operations."""

    def __init__(self, storage: dict[str, Any] | None = None):
        self._store: dict[str, dict[str, Any]] = storage or {}
        self._next_id = 1

    def handle_request(
        self, method: str, path: str, body: str | None = None,
        query_string: str = ""
    ) -> tuple[int, dict[str, Any]]:
        """Route and handle one HTTP request.

        Parses ``path`` with ``urlparse`` into path parts and parses
        ``query_string`` with ``parse_qs``, then dispatches via
        ``_match_route``. Returns the matched handler's
        ``(status, payload)`` tuple, or ``(404, {"error": "Not found",
        "path": path})`` when no route matches.
        """
        parsed = urlparse(path)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        params = parse_qs(query_string)
        handler = self._match_route(method, path_parts, params, body)
        if handler:
            result = handler()
            return result  # type: ignore[no-any-return]
        return 404, {"error": "Not found", "path": path}

    def _match_route(
        self, method: str, parts: list[str], params: dict, body: str | None
    ) -> Callable[..., Any] | None:
        """Dispatch path parts to a route handler.

        Branches (in order):
        - ["api", "v1", "health"] -> self._health_check
        - ["api", "v1", "stats"] -> self._get_stats
        - ["api", "v1", "content"] -> self._route_content(method, params, body)
        - ["api", "v1", "content", "search"] + GET -> lambda: self._search_content(params)
        - ["api", "v1", "content", "export"] + GET -> lambda: self._export_content(params)
        - len(parts)==4 and parts[:3]==["api", "v1", "content"] -> self._route_content_item(method, parts[3], body)
        - otherwise -> None (caller returns 404)
        """
        if parts == ["api", "v1", "health"]:
            return self._health_check
        if parts == ["api", "v1", "stats"]:
            return self._get_stats
        if parts == ["api", "v1", "content"]:
            return self._route_content(method, params, body)
        if parts == ["api", "v1", "content", "search"] and method == "GET":
            return lambda: self._search_content(params)
        if parts == ["api", "v1", "content", "export"] and method == "GET":
            return lambda: self._export_content(params)
        if len(parts) == 4 and parts[:3] == ["api", "v1", "content"]:
            return self._route_content_item(method, parts[3], body)
        return None

    def _route_content(
        self, method: str, params: dict, body: str | None
    ) -> Callable[..., Any] | None:
        """Dispatch /api/v1/content requests by HTTP method.

        Inspects only ``method`` (``params`` and ``body`` are captured by
        the returned closure, not inspected here). Returns:

        - ``"GET"``  -> a zero-arg callable that runs
          ``self._list_content(params)`` -> ``(200, {items, total, page,
          per_page})`` (or ``(400, {error})`` on non-integer page/per_page).
        - ``"POST"`` -> a zero-arg callable that runs
          ``self._create_content(body)`` -> ``(201, {item})`` on success,
          ``(400, {error})`` on a missing/invalid body.
        - any other method -> ``None`` (the caller maps this to 404/405).
        """
        if method == "GET":
            return lambda: self._list_content(params)
        if method == "POST":
            return lambda: self._create_content(body)
        return None

    def _route_content_item(
        self, method: str, item_id: str, body: str | None
    ) -> Callable[..., Any] | None:
        """Dispatch /api/v1/content/{id} requests by HTTP method.

        Inspects only ``method`` (``item_id`` and ``body`` are captured by
        the returned closure, not inspected here). Returns:

        - ``"GET"``    -> a zero-arg callable that runs
          ``self._get_content(item_id)`` -> ``(200, {item})`` on a match,
          ``(404, {error})`` when the id is absent.
        - ``"PUT"``    -> a zero-arg callable that runs
          ``self._update_content(item_id, body)`` -> ``(200, {item})`` on
          success, ``(404, {error})`` / ``(400, {error})`` on a missing id
          or missing/invalid body.
        - ``"DELETE"`` -> a zero-arg callable that runs
          ``self._delete_content(item_id)`` -> ``(200, {deleted, id})`` on a
          match, ``(404, {error})`` when the id is absent.
        - any other method -> ``None`` (the caller maps this to 404/405).
        """
        if method == "GET":
            return lambda: self._get_content(item_id)
        if method == "PUT":
            return lambda: self._update_content(item_id, body)
        if method == "DELETE":
            return lambda: self._delete_content(item_id)
        return None

    def _list_content(self, params: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
        """List content items with pagination.

        Reads the optional page (default 1) and per_page (default 20)
        query parameters from params. Returns (400, {"error": ...})
        when either page or per_page is not an integer. Otherwise
        per_page is capped at 100 and the method returns
        (200, {"items": [...], "total": int, "page": int,
        "per_page": int}) where items is the requested page slice of
        the store and total is the full item count.
        """
        items = list(self._store.values())
        # Pagination
        try:
            page = int(params.get("page", ["1"])[0])
            per_page = int(params.get("per_page", ["20"])[0])
        except ValueError:
            return 400, {"error": "Query parameters 'page' and 'per_page' must be integers"}
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

    def _get_content(self, item_id: str) -> tuple[int, dict[str, Any]]:
        """Look up a content item by id.

        Looks up ``item_id`` in the store. Returns ``(404, {"error": ...})``
        when the item is not found. Returns ``(200, {"item": <item>})`` when
        the item is found.
        """
        item = self._store.get(item_id)
        if item is None:
            return 404, {"error": f"Content item '{item_id}' not found"}
        return 200, {"item": item}

    def _create_content(self, body: str | None) -> tuple[int, dict[str, Any]]:
        """Create a new content item from a JSON request body.

        Returns ``(400, {"error": "Request body is required"})`` when the
        body is missing or empty. Returns ``(400, {"error": "Invalid JSON in
        request body"})`` when the body is not valid JSON. Returns
        ``(400, {"error": "Request body must be a JSON object"})`` when the
        parsed body is not a JSON object (dict). Otherwise builds an item
        (id from ``self._next_id``, title/description/link/tags with
        defaults, created_at/updated_at), stores it in ``self._store``, and
        returns ``(201, {"item": <item>})``.
        """
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

    def _update_content(self, item_id: str, body: str | None) -> tuple[int, dict[str, Any]]:
        """Partially update an existing content item from a JSON body.

        Returns ``(404, {"error": "Content item '<item_id>' not found"})``
        when ``item_id`` is not in ``self._store``. Returns
        ``(400, {"error": "Request body is required"})`` when the body is
        missing or empty. Returns ``(400, {"error": "Invalid JSON in request
        body"})`` when the body is not valid JSON. Returns
        ``(400, {"error": "Request body must be a JSON object"})`` when the
        parsed body is not a JSON object (dict). Otherwise partial-updates the
        stored item: for each of title/description/link/tags present in the
        parsed data it sets ``item[key]``, always refreshes
        ``item["updated_at"]`` to ``now(UTC).isoformat()``, and returns
        ``(200, {"item": <item>})``.
        """
        if item_id not in self._store:
            return 404, {"error": f"Content item '{item_id}' not found"}
        if not body:
            return 400, {"error": "Request body is required"}
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return 400, {"error": "Invalid JSON in request body"}
        if not isinstance(data, dict):
            return 400, {"error": "Request body must be a JSON object"}
        item = self._store[item_id]
        for key in ("title", "description", "link", "tags"):
            if key in data:
                item[key] = data[key]
        item["updated_at"] = datetime.now(timezone.utc).isoformat()
        return 200, {"item": item}

    def _delete_content(self, item_id: str) -> tuple[int, dict[str, Any]]:
        """Delete an existing content item by id.

        Returns ``(404, {"error": "Content item '<item_id>' not found"})``
        when ``item_id`` is not in ``self._store``. Otherwise removes the
        item from ``self._store`` (``pop``) and returns
        ``(200, {"deleted": True, "id": item_id})``.
        """
        if item_id not in self._store:
            return 404, {"error": f"Content item '{item_id}' not found"}
        self._store.pop(item_id)
        return 200, {"deleted": True, "id": item_id}

    def _search_content(self, params: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
        """Search content items by a case-insensitive substring query.

        Reads ``q = params.get("q", [""])[0]``. When ``q`` is empty, returns
        ``(400, {"error": "Search query parameter 'q' is required"})``.
        Otherwise performs a case-insensitive substring match of ``q`` against
        each item's ``title`` + ``description`` (lowercased), collecting matching
        items into ``results``, and returns
        ``(200, {"results": results, "total": len(results), "query": q})``.
        """
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

    def _export_content(self, params: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
        fmt = params.get("format", ["json"])[0]
        items = list(self._store.values())
        return 200, {"format": fmt, "items": items, "total": len(items)}

    def _health_check(self) -> tuple[int, dict[str, Any]]:
        return 200, {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

    def _get_stats(self) -> tuple[int, dict[str, Any]]:
        return 200, {
            "total_items": len(self._store),
            "tags": self._collect_tags(),
        }

    def _collect_tags(self) -> dict[str, int]:
        tag_counts: dict[str, int] = {}
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
