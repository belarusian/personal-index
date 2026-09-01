"""Tests for content router module."""


from personal_index.content_router.handler import PassThroughHandler, TypeHandler
from personal_index.content_router.route import Route, RouteMatcher
from personal_index.content_router.router import ContentRouter


class TestRouteMatcher:
    def test_add_and_match(self) -> None:
        matcher = RouteMatcher()
        matcher.add_route(Route(
            name="test",
            pattern="article",
            handler=lambda c: c,
        ))
        route = matcher.match({"type": "article"})
        assert route is not None
        assert route.name == "test"

    def test_match_url(self) -> None:
        matcher = RouteMatcher()
        matcher.add_route(Route(
            name="blog",
            pattern="blog",
            handler=lambda c: c,
        ))
        route = matcher.match({"url": "https://example.com/blog/post"})
        assert route is not None

    def test_match_wildcard(self) -> None:
        matcher = RouteMatcher()
        matcher.add_route(Route(
            name="catchall",
            pattern="*",
            handler=lambda c: c,
        ))
        route = matcher.match({"type": "anything"})
        assert route is not None

    def test_match_conditions(self) -> None:
        matcher = RouteMatcher()
        matcher.add_route(Route(
            name="premium",
            pattern="article",
            handler=lambda c: c,
            conditions={"premium": True},
        ))
        route = matcher.match({"type": "article", "premium": True})
        assert route is not None
        route2 = matcher.match({"type": "article", "premium": False})
        assert route2 is None

    def test_match_priority(self) -> None:
        matcher = RouteMatcher()
        matcher.add_route(Route(name="low", pattern="*", handler=lambda c: c, priority=1))
        matcher.add_route(Route(name="high", pattern="*", handler=lambda c: c, priority=10))
        route = matcher.match({"type": "test"})
        assert route is not None
        assert route.name == "high"

    def test_match_all(self) -> None:
        matcher = RouteMatcher()
        matcher.add_route(Route(name="r1", pattern="*", handler=lambda c: c))
        matcher.add_route(Route(name="r2", pattern="*", handler=lambda c: c))
        routes = matcher.match_all({"type": "test"})
        assert len(routes) == 2


class TestContentRouter:
    def test_route_with_match(self) -> None:
        router = ContentRouter()
        router.add_route(Route(
            name="test",
            pattern="article",
            handler=lambda c: {**c, "routed": True},
        ))
        result = router.route({"type": "article"})
        assert result["routed"] is True

    def test_route_no_match(self) -> None:
        router = ContentRouter()
        result = router.route({"type": "unknown"})
        assert result == {"type": "unknown"}

    def test_route_default_handler(self) -> None:
        router = ContentRouter()
        router.default_handler = PassThroughHandler()
        result = router.route({"type": "unknown"})
        assert result == {"type": "unknown"}

    def test_route_batch(self) -> None:
        router = ContentRouter()
        router.add_route(Route(
            name="test",
            pattern="*",
            handler=lambda c: {**c, "processed": True},
        ))
        items = [{"id": "1"}, {"id": "2"}]
        results = router.route_batch(items)
        assert all(r["processed"] for r in results)

    def test_register_handler(self) -> None:
        router = ContentRouter()
        handler = TypeHandler()
        router.register_handler(handler)
        assert router.get_handler(handler.name) is handler


class TestContentHandler:
    def test_passthrough(self) -> None:
        handler = PassThroughHandler()
        result = handler.handle({"id": "1", "title": "Test"})
        assert result == {"id": "1", "title": "Test"}

    def test_type_handler(self) -> None:
        handler = TypeHandler(supported_types=["article"])
        result = handler.handle({"type": "article", "title": "T"})
        assert result["processed_by"] == "type_handler"
        assert result["content_type"] == "article"

    def test_can_handle(self) -> None:
        handler = TypeHandler(supported_types=["article"])
        assert handler.can_handle({"type": "article"}) is True
        assert handler.can_handle({"type": "video"}) is False
