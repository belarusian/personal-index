"""Content router for directing content to handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from personal_index.content_router.handler import ContentHandler
from personal_index.content_router.route import Route, RouteMatcher


@dataclass
class ContentRouter:
    """Routes content items to appropriate handlers.

    Attributes:
        matcher: Route matcher for finding routes.
        handlers: Registered content handlers.
        default_handler: Handler used when no route matches.
    """

    matcher: RouteMatcher = field(default_factory=RouteMatcher)
    handlers: dict[str, ContentHandler] = field(default_factory=dict)
    default_handler: ContentHandler | None = None

    def register_handler(self, handler: ContentHandler) -> None:
        """Register a content handler.

        Args:
            handler: Handler to register.
        """
        self.handlers[handler.name] = handler

    def add_route(self, route: Route) -> None:
        """Add a route to the router.

        Args:
            route: Route to add.
        """
        self.matcher.add_route(route)

    def route(self, content: dict[str, Any]) -> dict[str, Any]:
        """Route a content item to its handler.

        Args:
            content: Content item to route.

        Returns:
            Processed content item.
        """
        matched = self.matcher.match(content)

        if matched:
            return cast(dict[str, Any], matched.handler(content))

        if self.default_handler:
            return self.default_handler.handle(content)

        return dict(content)

    def route_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Route multiple content items.

        Args:
            items: List of content items.

        Returns:
            List of processed content items.
        """
        return [self.route(item) for item in items]

    def get_handler(self, name: str) -> ContentHandler | None:
        """Get a handler by name.

        Args:
            name: Handler name.

        Returns:
            Handler or None if not found.
        """
        return self.handlers.get(name)
