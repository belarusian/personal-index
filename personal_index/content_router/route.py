"""Route definitions for content routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Route:
    """A single route definition.

    Attributes:
        name: Route name.
        pattern: URL or content pattern to match.
        handler: Handler function for matched content.
        priority: Route priority (higher = first).
        conditions: Additional matching conditions.
    """

    name: str
    pattern: str
    handler: Callable[[dict[str, Any]], Any]
    priority: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteMatcher:
    """Matches content against route patterns.

    Attributes:
        routes: List of registered routes.
    """

    routes: list[Route] = field(default_factory=list)

    def add_route(self, route: Route) -> None:
        """Add a route to the matcher.

        Args:
            route: Route to add.
        """
        self.routes.append(route)
        self.routes.sort(key=lambda r: r.priority, reverse=True)

    def match(self, content: dict[str, Any]) -> Route | None:
        """Find the first matching route for content.

        Args:
            content: Content item to match.

        Returns:
            Matching Route or None.
        """
        for route in self.routes:
            if self._matches(route, content):
                return route
        return None

    def match_all(self, content: dict[str, Any]) -> list[Route]:
        """Find all matching routes for content.

        Args:
            content: Content item to match.

        Returns:
            List of matching routes.
        """
        return [route for route in self.routes if self._matches(route, content)]

    def _matches(self, route: Route, content: dict[str, Any]) -> bool:
        """Check if content matches a route.

        Args:
            route: Route to check.
            content: Content item.

        Returns:
            True if content matches the route.
        """
        # Check pattern against URL or type
        url = content.get("url", "")
        content_type = content.get("type", "")

        pattern_matches = (
            route.pattern in url
            or route.pattern == content_type
            or route.pattern == "*"
        )

        if not pattern_matches:
            return False

        # Check conditions
        for key, value in route.conditions.items():
            if content.get(key) != value:
                return False

        return True
