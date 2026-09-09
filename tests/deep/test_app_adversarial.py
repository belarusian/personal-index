"""Adversarial deep tests for personal_index.app (PersonalIndexApp).

Contract source: personal_index/app.py module + method docstrings (the
"code is the truth" section). Pins the documented constructor invariants,
the lazy property guard/caching paths, initialize() idempotence, the
process_content filter guard (short content is NOT indexed), the search
entry-unwrapping contract, add_interest persistence + priority clamp, and
the get_stats field set.

DEFECT (QA-16): the negative-slice "top N" leak class (QA-1/QA-2/QA-3/QA-4/
QA-5/QA-15) has a NEW public site missed by QA-4's sweep table (which listed
content_search.SearchIndex.get_suggestions but NOT content_search.SearchIndex.search):
``SearchIndex.search(query, limit=-1)`` returns ``ranked[:-1]`` (all-but-last)
instead of ``[]``. Reachable through the public entry point
``PersonalIndexApp.search(query, limit=-1)`` -> ContentSearch.search ->
SearchIndex.search. The ``0`` bound is correct (returns ``[]``); the negative
bound is not. Pinned xfail-strict below.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.content_search import ContentSearch, SearchIndex
from personal_index.config.models import AppConfig

# Content long enough to pass the default ContentFilter min_content_length=100
# and to contain a shared searchable token ("guide") plus a distinct token.
_LONG = "the guide to programming languages and their design " * 4


def _make_app(tmp: str) -> PersonalIndexApp:
    return PersonalIndexApp(
        config_path=os.path.join(tmp, "cfg.yaml"),
        data_dir=os.path.join(tmp, "data"),
    )


def _index_three(app: PersonalIndexApp) -> None:
    """Index three distinct items that all match the token 'guide'."""
    app.process_content("http://a", _LONG + " python scripting", "python guide")
    app.process_content("http://b", _LONG + " java enterprise", "java guide")
    app.process_content("http://c", _LONG + " go concurrency", "go guide")


# ---------------------------------------------------------------------------
# Constructor invariants
# ---------------------------------------------------------------------------
def test_constructor_sets_no_io_state():
    app = PersonalIndexApp(config_path="cfg.yaml", data_dir=".personal_index")
    assert app.config_path == "cfg.yaml"
    assert app.data_dir == ".personal_index"
    assert app._config is None
    assert app._interest_store is None
    assert app._search_index is None
    assert app._content_search is None
    assert app._scheduler is None
    assert app._pipeline is None
    assert app._initialized is False


def test_constructor_does_not_create_data_dir():
    with tempfile.TemporaryDirectory() as tmp:
        dd = os.path.join(tmp, "should_not_exist")
        PersonalIndexApp(config_path=os.path.join(tmp, "c.yaml"), data_dir=dd)
        assert not os.path.exists(dd)


# ---------------------------------------------------------------------------
# config property: missing file -> defaults, caching
# ---------------------------------------------------------------------------
def test_config_missing_file_returns_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        cfg = app.config
        assert isinstance(cfg, AppConfig)
        # load_config returns the default AppConfig() for a missing file.
        assert cfg.data_dir == ".personal_index"


def test_config_is_cached():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        first = app.config
        second = app.config
        assert first is second


# ---------------------------------------------------------------------------
# initialize() idempotence
# ---------------------------------------------------------------------------
def test_initialize_creates_data_dir_and_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        assert not os.path.exists(app.data_dir)
        app.initialize()
        assert os.path.isdir(app.data_dir)
        assert app._initialized is True
        # Second call is a no-op (guard path).
        app.initialize()
        assert app._initialized is True


def test_initialize_forces_component_construction():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        app.initialize()
        assert app._config is not None
        assert app._interest_store is not None
        assert app._search_index is not None
        assert app._content_search is not None
        assert app._pipeline is not None


# ---------------------------------------------------------------------------
# process_content: filter guard + indexing
# ---------------------------------------------------------------------------
def test_process_content_short_content_not_indexed():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        res = app.process_content("http://x", "tiny", "tiny title")
        assert res.get("passes_filter") is False
        assert len(app.search_index._items) == 0


def test_process_content_long_content_indexed():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        res = app.process_content("http://x", _LONG + " python", "python guide")
        assert res.get("passes_filter") is True
        assert len(app.search_index._items) == 1
        # The indexed item id is the url.
        assert "http://x" in app.search_index._items


def test_process_content_title_fallback_untitled():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        res = app.process_content("http://x", _LONG + " python", "")
        # extract step falls back to "Untitled" when title is empty.
        assert res.get("title") == "Untitled"


def test_process_content_empty_raw_content():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        res = app.process_content("http://x", "", "a title")
        # Empty raw content -> empty extracted text -> filter rejects.
        assert res.get("passes_filter") is False
        assert res.get("extracted_text") == ""


# ---------------------------------------------------------------------------
# search: empty index, entry unwrapping, guard bounds
# ---------------------------------------------------------------------------
def test_search_empty_index_returns_empty_list():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        assert app.search("guide") == []


def test_search_unwraps_item_and_sets_score():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        _index_three(app)
        out = app.search("guide", limit=3)
        assert len(out) == 3
        for item in out:
            assert "id" in item
            assert "score" in item
            # content key is stripped by _build_entry.
            assert "content" not in item


def test_search_limit_zero_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        _index_three(app)
        assert app.search("guide", limit=0) == []


def test_search_limit_two_returns_two():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        _index_three(app)
        assert len(app.search("guide", limit=2)) == 2


def test_search_no_match_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        _index_three(app)
        assert app.search("zzzznotthere") == []


def test_search_whitespace_query_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        _index_three(app)
        assert app.search("   ") == []


# ---------------------------------------------------------------------------
# add_interest: persistence + priority clamp
# ---------------------------------------------------------------------------
def test_add_interest_persists():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        app.add_interest("python", keywords=["python", "py"])
        interests = app.interest_store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "python"
        assert interests[0].keywords == ["python", "py"]


def test_add_interest_priority_clamped_to_10():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        app.add_interest("big", priority=99)
        assert app.interest_store.list_all()[0].priority == 10


def test_add_interest_priority_clamped_to_1():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        app.add_interest("small", priority=-5)
        assert app.interest_store.list_all()[0].priority == 1


def test_add_interest_default_keywords_empty():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        app.add_interest("bare")
        it = app.interest_store.list_all()[0]
        assert it.keywords == []
        assert it.url_patterns == []


# ---------------------------------------------------------------------------
# get_stats: field set
# ---------------------------------------------------------------------------
def test_get_stats_fields():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        _index_three(app)
        app.add_interest("python", keywords=["python"])
        stats = app.get_stats()
        assert set(stats.keys()) == {
            "indexed_items",
            "interests",
            "scheduled_jobs",
            "pipeline_steps",
            "enabled_steps",
            "data_dir",
        }
        assert stats["indexed_items"] == 3
        assert stats["interests"] == 1
        assert stats["data_dir"] == app.data_dir
        assert stats["pipeline_steps"] == 4
        assert stats["enabled_steps"] == ["extract", "filter", "score", "tag"]


# ---------------------------------------------------------------------------
# content_search.SearchIndex direct: the negative-slice "top N" class
# ---------------------------------------------------------------------------
def test_searchindex_search_limit_zero_guard():
    idx = SearchIndex()
    idx.add_item({"id": "a", "url": "a", "title": "python guide", "content": _LONG + " python"})
    idx.add_item({"id": "b", "url": "b", "title": "java guide", "content": _LONG + " java"})
    idx.add_item({"id": "c", "url": "c", "title": "go guide", "content": _LONG + " go"})
    r = idx.search("guide", limit=0)
    assert r["results"] == []
    assert r["total"] == 3


def test_searchindex_search_limit_two():
    idx = SearchIndex()
    idx.add_item({"id": "a", "url": "a", "title": "python guide", "content": _LONG + " python"})
    idx.add_item({"id": "b", "url": "b", "title": "java guide", "content": _LONG + " java"})
    idx.add_item({"id": "c", "url": "c", "title": "go guide", "content": _LONG + " go"})
    r = idx.search("guide", limit=2)
    assert len(r["results"]) == 2
    assert r["total"] == 3


def test_contentsearch_search_empty_index():
    cs = ContentSearch()
    r = cs.search("guide", limit=5)
    assert r == {"results": [], "total": 0, "query": "guide"}


# ---------------------------------------------------------------------------
# DEFECT: negative-slice "top N" leak (QA-16)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="QA-16: SearchIndex.search(limit=-1) leaks ranked[:-1] instead of []",
)
def test_searchindex_search_limit_negative_returns_empty():
    # Contract (negative-slice "top N" class, QA-1..QA-5/QA-15): a negative
    # bound must yield an empty list, matching the 0 guard.
    idx = SearchIndex()
    idx.add_item({"id": "a", "url": "a", "title": "python guide", "content": _LONG + " python"})
    idx.add_item({"id": "b", "url": "b", "title": "java guide", "content": _LONG + " java"})
    idx.add_item({"id": "c", "url": "c", "title": "go guide", "content": _LONG + " go"})
    r = idx.search("guide", limit=-1)
    assert r["results"] == []


@pytest.mark.xfail(
    strict=True,
    reason="QA-16: app.search(limit=-1) leaks all-but-last instead of []",
)
def test_app_search_limit_negative_returns_empty():
    # Reachable through the public entry point PersonalIndexApp.search.
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp)
        _index_three(app)
        assert app.search("guide", limit=-1) == []


# ---------------------------------------------------------------------------
# End-to-end CLI run
# ---------------------------------------------------------------------------
def test_cli_boots_and_app_importable():
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert "Personal Index" in proc.stdout
    # app importable in the same interpreter.
    import personal_index.app as app_mod  # noqa: F401

    assert callable(app_mod.PersonalIndexApp)


def test_cli_search_empty_index_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index.cli", "search", "python",
             "--data-dir", tmp],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
        assert "No indexed content found" in proc.stdout
