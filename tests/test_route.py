"""Tests for route matching."""

from personal_index.content_router.route import Route, RouteMatcher


def dummy_handler(content):
    return content


class TestRoute:
    def test_creation(self):
        r = Route(name="test", pattern="*", handler=dummy_handler)
        assert r.priority == 0
        assert r.conditions == {}


class TestRouteMatcher:
    def test_add_route(self):
        m = RouteMatcher()
        r = Route(name="test", pattern="*", handler=dummy_handler)
        m.add_route(r)
        assert len(m.routes) == 1

    def test_match_wildcard(self):
        m = RouteMatcher()
        m.add_route(Route(name="catchall", pattern="*", handler=dummy_handler))
        result = m.match({"url": "https://example.com"})
        assert result is not None
        assert result.name == "catchall"

    def test_match_url(self):
        m = RouteMatcher()
        m.add_route(Route(name="api", pattern="/api", handler=dummy_handler))
        result = m.match({"url": "https://example.com/api/users"})
        assert result is not None
        assert result.name == "api"

    def test_match_type(self):
        m = RouteMatcher()
        m.add_route(Route(name="article", pattern="article", handler=dummy_handler))
        result = m.match({"url": "", "type": "article"})
        assert result is not None

    def test_no_match(self):
        m = RouteMatcher()
        m.add_route(Route(name="api", pattern="/api", handler=dummy_handler))
        result = m.match({"url": "https://example.com/other"})
        assert result is None

    def test_match_priority(self):
        m = RouteMatcher()
        m.add_route(Route(name="low", pattern="*", handler=dummy_handler, priority=1))
        m.add_route(Route(name="high", pattern="*", handler=dummy_handler, priority=10))
        result = m.match({"url": "any"})
        assert result.name == "high"

    def test_match_conditions(self):
        m = RouteMatcher()
        m.add_route(Route(name="api", pattern="/api", handler=dummy_handler, conditions={"format": "json"}))
        result = m.match({"url": "/api/data", "format": "json"})
        assert result is not None

    def test_match_conditions_fail(self):
        m = RouteMatcher()
        m.add_route(Route(name="api", pattern="/api", handler=dummy_handler, conditions={"format": "json"}))
        result = m.match({"url": "/api/data", "format": "xml"})
        assert result is None

    def test_match_all(self):
        m = RouteMatcher()
        m.add_route(Route(name="all1", pattern="*", handler=dummy_handler))
        m.add_route(Route(name="all2", pattern="*", handler=dummy_handler))
        results = m.match_all({"url": "any"})
        assert len(results) == 2
