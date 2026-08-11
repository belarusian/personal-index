"""Content router module - route content to appropriate handlers."""

from personal_index.content_router.router import ContentRouter
from personal_index.content_router.route import Route, RouteMatcher
from personal_index.content_router.handler import ContentHandler

__all__ = [
    "ContentHandler",
    "ContentRouter",
    "Route",
    "RouteMatcher",
]
