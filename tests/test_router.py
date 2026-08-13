"""Tests for content router."""

from personal_index.content_router.handler import PassThroughHandler, TypeHandler
from personal_index.content_router.route import Route, RouteMatcher
from personal_index.content_router.router import ContentRouter


def handler_fn(content):
    content["handled"] = True
    return content


class TestContentRouter:
    def test_route_with_match(self):
        router = ContentRouter()
        router.add_route(Route(name="test", pattern="/api", handler=handler_fn))
        result = router.route({"url": "/api/data"})
        assert result["handled"] is True

    def test_route_no_match_default(self):
        router = ContentRouter()
        router.default_handler = PassThroughHandler()
        result = router.route({"url": "/other"})
        assert result["url"] == "/other"

    def test_route_no_match_no_default(self):
        router = ContentRouter()
        result = router.route({"url": "/other"})
        assert result["url"] == "/other"

    def test_route_batch(self):
        router = ContentRouter()
        router.add_route(Route(name="test", pattern="*", handler=handler_fn))
        items = [{"url": "a"}, {"url": "b"}]
        results = router.route_batch(items)
        assert len(results) == 2
        assert all(r["handled"] for r in results)

    def test_register_handler(self):
        router = ContentRouter()
        h = PassThroughHandler()
        router.register_handler(h)
        assert router.get_handler("passthrough") is not None

    def test_get_handler_missing(self):
        router = ContentRouter()
        assert router.get_handler("missing") is None


class TestPassThroughHandler:
    def test_passthrough(self):
        h = PassThroughHandler()
        result = h.handle({"key": "val"})
        assert result == {"key": "val"}

    def test_can_handle_any(self):
        h = PassThroughHandler()
        assert h.can_handle({"type": "anything"}) is True


class TestTypeHandler:
    def test_type_handler(self):
        h = TypeHandler()
        result = h.handle({"type": "article"})
        assert result["processed_by"] == "type_handler"
        assert result["content_type"] == "article"

    def test_can_handle_specific(self):
        h = TypeHandler(supported_types=["article"])
        assert h.can_handle({"type": "article"}) is True
        assert h.can_handle({"type": "video"}) is False
