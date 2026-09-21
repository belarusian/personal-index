"""Adversarial deep tests for personal_index.content_router (never-probed module).

Contracts attacked:
- Route dataclass: name/pattern/handler/priority/conditions defaults.
- RouteMatcher.add_route: priority sort (higher first), idempotence, duplicates.
- RouteMatcher.match: first-match-wins by priority; url substring; type equality;
  "*" wildcard; conditions gate; None/empty/unicode content.
- RouteMatcher.match_all: returns all matches in priority order.
- ContentRouter.route: matched handler, default_handler fallback, no-match passthrough
  (returns a COPY, not the same object).
- ContentRouter.route_batch: element-wise routing.
- ContentRouter.get_handler: found / not-found.
- ContentHandler.can_handle: PassThroughHandler supports "*"; TypeHandler contract.
- PassThroughHandler.handle / TypeHandler.handle: return a copy, not the input.

At least one end-to-end run through the installed CLI is covered by the broader
deep suite; this file focuses on the router's pure-Python contract.
"""

from __future__ import annotations

import pytest

from personal_index.content_router.handler import (
    ContentHandler,
    PassThroughHandler,
    TypeHandler,
)
from personal_index.content_router.route import Route, RouteMatcher
from personal_index.content_router.router import ContentRouter


def _handler(name: str):
    """Return a plain CALLABLE handler (Route.handler is typed Callable).

    Note: the concrete ContentHandler subclasses (PassThroughHandler,
    TypeHandler) are dataclass INSTANCES, not callables, so they cannot be
    used directly as a Route.handler -- that mismatch is itself probed below.
    """

    def _h(content):
        out = dict(content)
        out["handled_by"] = name
        return out

    return _h


def _instance_handler(name: str):
    """Return a real ContentHandler INSTANCE (has .handle and .name)."""

    class _H(ContentHandler):
        def __init__(self, name):
            self.name = name
            self.supported_types = ["*"]

        def handle(self, content):
            out = dict(content)
            out["handled_by"] = self.name
            return out

    return _H(name)


# ---------------------------------------------------------------------------
# Route dataclass
# ---------------------------------------------------------------------------
def test_route_defaults():
    h = _handler("h")
    r = Route(name="r", pattern="*", handler=h)
    assert r.priority == 0
    assert r.conditions == {}


def test_route_explicit_fields():
    h = _handler("h")
    r = Route(name="r", pattern="news", handler=h, priority=5, conditions={"lang": "en"})
    assert r.priority == 5
    assert r.conditions == {"lang": "en"}


# ---------------------------------------------------------------------------
# RouteMatcher.add_route: priority ordering + idempotence + duplicates
# ---------------------------------------------------------------------------
def test_add_route_sorts_by_priority_desc():
    m = RouteMatcher()
    m.add_route(Route(name="low", pattern="*", handler=_handler("low"), priority=1))
    m.add_route(Route(name="high", pattern="*", handler=_handler("high"), priority=10))
    m.add_route(Route(name="mid", pattern="*", handler=_handler("mid"), priority=5))
    assert [r.name for r in m.routes] == ["high", "mid", "low"]


def test_add_route_negative_priority_sorts_last():
    m = RouteMatcher()
    m.add_route(Route(name="pos", pattern="*", handler=_handler("pos"), priority=1))
    m.add_route(Route(name="neg", pattern="*", handler=_handler("neg"), priority=-100))
    assert [r.name for r in m.routes] == ["pos", "neg"]


def test_add_route_idempotent_for_same_route_object():
    m = RouteMatcher()
    r = Route(name="r", pattern="*", handler=_handler("h"), priority=1)
    m.add_route(r)
    before = len(m.routes)
    # Adding a distinct but equal route is a duplicate; the contract does not
    # promise dedup, so we only assert the list stays a valid sorted list.
    m.add_route(Route(name="r", pattern="*", handler=_handler("h"), priority=1))
    assert len(m.routes) == before + 1
    # still sorted
    prios = [r.priority for r in m.routes]
    assert prios == sorted(prios, reverse=True)


# ---------------------------------------------------------------------------
# RouteMatcher.match: first-match-wins by priority
# ---------------------------------------------------------------------------
def test_match_first_by_priority():
    m = RouteMatcher()
    m.add_route(Route(name="low", pattern="*", handler=_handler("low"), priority=1))
    m.add_route(Route(name="high", pattern="*", handler=_handler("high"), priority=10))
    got = m.match({"url": "http://x", "type": "article"})
    assert got is not None
    assert got.name == "high"


def test_match_url_substring():
    m = RouteMatcher()
    m.add_route(Route(name="news", pattern="news", handler=_handler("news")))
    got = m.match({"url": "http://example.com/news/1", "type": "article"})
    assert got is not None and got.name == "news"


def test_match_url_substring_no_match():
    m = RouteMatcher()
    m.add_route(Route(name="news", pattern="news", handler=_handler("news")))
    assert m.match({"url": "http://example.com/blog/1", "type": "article"}) is None


def test_match_type_equality():
    m = RouteMatcher()
    m.add_route(Route(name="video", pattern="video", handler=_handler("video")))
    got = m.match({"url": "http://x", "type": "video"})
    assert got is not None and got.name == "video"


def test_match_wildcard():
    m = RouteMatcher()
    m.add_route(Route(name="all", pattern="*", handler=_handler("all")))
    got = m.match({"url": "", "type": ""})
    assert got is not None and got.name == "all"


def test_match_conditions_gate_pass():
    m = RouteMatcher()
    m.add_route(
        Route(name="en", pattern="*", handler=_handler("en"), conditions={"lang": "en"})
    )
    got = m.match({"url": "http://x", "type": "article", "lang": "en"})
    assert got is not None and got.name == "en"


def test_match_conditions_gate_fail():
    m = RouteMatcher()
    m.add_route(
        Route(name="en", pattern="*", handler=_handler("en"), conditions={"lang": "en"})
    )
    assert m.match({"url": "http://x", "type": "article", "lang": "fr"}) is None


def test_match_empty_content_wildcard():
    m = RouteMatcher()
    m.add_route(Route(name="all", pattern="*", handler=_handler("all")))
    got = m.match({})
    assert got is not None and got.name == "all"


def test_match_unicode_content():
    m = RouteMatcher()
    m.add_route(Route(name="u", pattern="héllo", handler=_handler("u")))
    got = m.match({"url": "http://x/héllo/wörld", "type": "article"})
    assert got is not None and got.name == "u"


def test_match_none_url_treated_as_empty():
    # content.get("url", "") returns "" when key absent; a None value is distinct.
    m = RouteMatcher()
    m.add_route(Route(name="all", pattern="*", handler=_handler("all")))
    # wildcard matches regardless of url value
    got = m.match({"url": None, "type": "article"})
    assert got is not None and got.name == "all"


def test_match_no_routes_returns_none():
    m = RouteMatcher()
    assert m.match({"url": "http://x", "type": "article"}) is None


# ---------------------------------------------------------------------------
# RouteMatcher.match_all
# ---------------------------------------------------------------------------
def test_match_all_returns_all_in_priority_order():
    m = RouteMatcher()
    m.add_route(Route(name="low", pattern="*", handler=_handler("low"), priority=1))
    m.add_route(Route(name="high", pattern="*", handler=_handler("high"), priority=10))
    got = m.match_all({"url": "http://x", "type": "article"})
    assert [r.name for r in got] == ["high", "low"]


def test_match_all_empty_when_no_match():
    m = RouteMatcher()
    m.add_route(Route(name="news", pattern="news", handler=_handler("news")))
    assert m.match_all({"url": "http://x/blog", "type": "article"}) == []


# ---------------------------------------------------------------------------
# ContentRouter.route
# ---------------------------------------------------------------------------
def test_route_matched_handler():
    r = ContentRouter()
    r.add_route(Route(name="news", pattern="news", handler=_handler("news")))
    out = r.route({"url": "http://x/news/1", "type": "article"})
    assert out["handled_by"] == "news"


def test_route_default_handler_fallback():
    r = ContentRouter()
    r.default_handler = _instance_handler("default")
    out = r.route({"url": "http://x/other", "type": "article"})
    assert out["handled_by"] == "default"


def test_route_no_match_no_default_returns_copy():
    r = ContentRouter()
    src = {"url": "http://x", "type": "article"}
    out = r.route(src)
    assert out == src
    assert out is not src  # must be a copy, not the same object


def test_route_matched_takes_precedence_over_default():
    r = ContentRouter()
    r.default_handler = _instance_handler("default")
    r.add_route(Route(name="news", pattern="news", handler=_handler("news")))
    out = r.route({"url": "http://x/news/1", "type": "article"})
    assert out["handled_by"] == "news"


def test_route_empty_content_no_match_returns_copy():
    r = ContentRouter()
    src = {}
    out = r.route(src)
    assert out == {}
    assert out is not src


# ---------------------------------------------------------------------------
# ContentRouter.route_batch
# ---------------------------------------------------------------------------
def test_route_batch_elementwise():
    r = ContentRouter()
    r.add_route(Route(name="news", pattern="news", handler=_handler("news")))
    items = [
        {"url": "http://x/news/1", "type": "article"},
        {"url": "http://x/blog/1", "type": "article"},
    ]
    out = r.route_batch(items)
    assert len(out) == 2
    assert out[0]["handled_by"] == "news"
    assert out[1] == items[1]  # no match -> passthrough copy


def test_route_batch_empty():
    r = ContentRouter()
    assert r.route_batch([]) == []


# ---------------------------------------------------------------------------
# ContentRouter.get_handler
# ---------------------------------------------------------------------------
def test_get_handler_found():
    r = ContentRouter()
    h = _instance_handler("h")
    r.register_handler(h)
    assert r.get_handler("h") is h


def test_get_handler_not_found():
    r = ContentRouter()
    assert r.get_handler("missing") is None


# ---------------------------------------------------------------------------
# ContentHandler.can_handle
# ---------------------------------------------------------------------------
def test_passthrough_can_handle_any_type():
    p = PassThroughHandler()
    assert p.can_handle({"type": "article"}) is True
    assert p.can_handle({"type": "video"}) is True
    assert p.can_handle({}) is True  # type defaults to "unknown", "*" matches


@pytest.mark.xfail(
    strict=True,
    reason="QA-70: TypeHandler.can_handle always returns False because TypeHandler.__post_init__ "
    "overrides the base without calling super().__post_init__(), leaving supported_types=None; "
    "the base can_handle returns False when supported_types is None, contradicting the base "
    "docstring ('True if handler supports this content type') and its sibling PassThroughHandler.",
)
def test_typehandler_can_handle_typed_content():
    # TypeHandler is a concrete handler whose purpose (per its docstring) is to
    # process content based on type. Its can_handle must therefore report True
    # for typed content, consistent with its sibling PassThroughHandler.
    t = TypeHandler()
    assert t.can_handle({"type": "article"}) is True


@pytest.mark.xfail(
    strict=True,
    reason="QA-70: TypeHandler.can_handle always returns False (supported_types=None, see "
    "test_typehandler_can_handle_typed_content); unknown-type content must also be accepted.",
)
def test_typehandler_can_handle_unknown_type():
    t = TypeHandler()
    assert t.can_handle({}) is True


# ---------------------------------------------------------------------------
# handle() returns a copy, not the input
# ---------------------------------------------------------------------------
def test_passthrough_handle_returns_copy():
    p = PassThroughHandler()
    src = {"url": "http://x", "type": "article"}
    out = p.handle(src)
    assert out == src
    assert out is not src


def test_typehandler_handle_returns_copy_and_annotates():
    t = TypeHandler()
    src = {"url": "http://x", "type": "article"}
    out = t.handle(src)
    assert out is not src
    assert out["processed_by"] == "type_handler"
    assert out["content_type"] == "article"
    # input must be unchanged
    assert "processed_by" not in src


def test_typehandler_handle_missing_type_defaults_unknown():
    t = TypeHandler()
    out = t.handle({"url": "http://x"})
    assert out["content_type"] == "unknown"


# ---------------------------------------------------------------------------
# End-to-end CLI run (installed CLI) — the router is not wired into the CLI,
# so this pins that the installed CLI still boots and `init` exits green.
# ---------------------------------------------------------------------------
def test_cli_init_runs_green(tmp_path):
    import subprocess
    import sys

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config = data_dir / "config.yaml"
    base = [sys.executable, "-m", "personal_index.cli", "--data-dir", str(data_dir)]
    init = subprocess.run(
        base + ["init", "--config", str(config)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert init.returncode == 0, init.stderr
