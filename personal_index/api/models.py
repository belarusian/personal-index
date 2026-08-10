"""Request and response models for the personal-index API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, TypeVar

T = TypeVar("T")


@dataclass
class APIResponse(Generic[T]):
    """Standard API response wrapper."""
    success: bool
    data: T | None = None
    error: str | None = None
    message: str | None = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {"success": self.success}
        if self.data is not None:
            if hasattr(self.data, "to_dict"):
                result["data"] = self.data.to_dict()
            elif isinstance(self.data, dict):
                result["data"] = self.data
            else:
                result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.message:
            result["message"] = self.message
        if self.meta:
            result["meta"] = self.meta
        return result

    @classmethod
    def ok(cls, data: T, message: str = "Success") -> "APIResponse[T]":
        return cls(success=True, data=data, message=message)

    @classmethod
    def error(cls, message: str, error_code: str | None = None) -> "APIResponse[T]":
        return cls(success=False, error=error_code or "error", message=message)


@dataclass
class PaginatedResponse(Generic[T]):
    """Paginated response with metadata."""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    def to_dict(self) -> Dict[str, Any]:
        items_data = []
        for item in self.items:
            if hasattr(item, "to_dict"):
                items_data.append(item.to_dict())
            elif isinstance(item, dict):
                items_data.append(item)
            else:
                items_data.append(item)
        return {
            "items": items_data,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


@dataclass
class SearchRequest:
    """Search request parameters."""
    q: str
    limit: int = 20
    offset: int = 0
    filters: Dict[str, str] = field(default_factory=dict)
    sort_by: str | None = None
    sort_order: str = "desc"

    def validate(self) -> List[str]:
        errors = []
        if not self.q or not self.q.strip():
            errors.append("Query cannot be empty")
        if self.limit < 1 or self.limit > 100:
            errors.append("Limit must be between 1 and 100")
        if self.offset < 0:
            errors.append("Offset must be non-negative")
        if self.sort_order not in ("asc", "desc"):
            errors.append("Sort order must be 'asc' or 'desc'")
        return errors


@dataclass
class SearchResponse:
    """Search response with results."""
    query: str
    results: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": self.results,
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class ErrorResponse:
    """Error response with details."""
    error: str
    message: str
    status_code: int = 400
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error": self.error,
            "message": self.message,
            "status_code": self.status_code,
        }
        if self.details:
            result["details"] = self.details
        return result


class APIError(Exception):
    """Base API exception."""
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "bad_request",
        details: Dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(APIError):
    """Resource not found."""
    def __init__(self, message: str = "Resource not found", details=None):
        super().__init__(message, status_code=404, error_code="not_found", details=details)


class ValidationError(APIError):
    """Request validation failed."""
    def __init__(self, message: str = "Validation failed", details=None):
        super().__init__(message, status_code=422, error_code="validation_error", details=details)


class UnauthorizedError(APIError):
    """Authentication required."""
    def __init__(self, message: str = "Authentication required", details=None):
        super().__init__(message, status_code=401, error_code="unauthorized", details=details)


class ForbiddenError(APIError):
    """Permission denied."""
    def __init__(self, message: str = "Permission denied", details=None):
        super().__init__(message, status_code=403, error_code="forbidden", details=details)
