"""Adversarial deep tests: defensive-load-crash CLASS sweep (QA-20).

Class home: ARCH-63 (docs/CONTRACTS.md "Defensive-load guard (binding)").
Per-site instances already filed: QA-11 (domains, CLOSED/fixed), QA-17
(content_pin, OPEN). This sweep re-runs the whole-codebase pattern
(`_load` that `json.load`s a file, checks `isinstance(data, dict)`, then
iterates `.items()` constructing a per-key object) and finds FIVE NEW
public sites whose `except` tuple does NOT cover the value-shape error a
non-dict value raises, so construction propagates out of `__init__` /
`__post_init__` instead of degrading to the empty state:

  1. personal_index/index.py            SearchIndex._load
  2. personal_index/search_index.py     SearchIndex._load
  3. personal_index/tags.py             TagStore._load
  4. personal_index/interests.py        InterestStore._load
  5. personal_index/migrations/base.py  MigrationStore._load

The contract (ARCH-63): a well-formed-but-wrong-shape value (a value that
is not a mapping) MUST yield the same empty state as a missing file and
MUST NOT raise out of construction. The five sites above violate it; they
are pinned xfail-strict below so the suite stays green while documenting
the defect. The already-safe sites (content_versioning, domains,
scheduler.ScheduleStore, content_pin top-level guard) are pinned as clean
armor.

Repro for each xfail: write the shown JSON to a temp file, construct the
store, assert the accessor reflects the empty state.
"""

from __future__ import annotations

import json

import pytest

from personal_index.index import SearchIndex as IndexSearchIndex
from personal_index.interests import InterestStore
from personal_index.migrations.base import MigrationStore
from personal_index.search_index import SearchIndex as SearchIndexStore
from personal_index.tags import TagStore


def _write(path, obj) -> str:
    with open(path, "w") as f:
        f.write(json.dumps(obj))
    return str(path)


# ---------------------------------------------------------------------------
# Site 1: personal_index/index.py SearchIndex._load
# ---------------------------------------------------------------------------
class TestIndexSearchIndex:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-20: index.py SearchIndex._load crashes (AttributeError) on "
        "non-dict page value; contract (ARCH-63) requires empty state",
    )
    def test_non_dict_page_value_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "idx.json", {"pages": {"u": "notadict"}, "word_index": {}})
        idx = IndexSearchIndex(db_path=p)
        assert idx.get_page_count() == 0
        assert idx.list_pages() == []

    def test_missing_file_yields_empty(self, tmp_path):
        idx = IndexSearchIndex(db_path=str(tmp_path / "nope.json"))
        assert idx.get_page_count() == 0

    def test_non_dict_top_level_yields_empty(self, tmp_path):
        p = _write(tmp_path / "idx.json", ["not", "a", "dict"])
        idx = IndexSearchIndex(db_path=p)
        assert idx.get_page_count() == 0

    def test_empty_dict_yields_empty(self, tmp_path):
        p = _write(tmp_path / "idx.json", {})
        idx = IndexSearchIndex(db_path=p)
        assert idx.get_page_count() == 0

    def test_valid_page_populates(self, tmp_path):
        p = _write(
            tmp_path / "idx.json",
            {"pages": {"http://x": {"url": "http://x", "title": "t", "content": "c"}},
             "word_index": {}},
        )
        idx = IndexSearchIndex(db_path=p)
        assert idx.get_page_count() == 1
        assert idx.get_page("http://x") is not None


# ---------------------------------------------------------------------------
# Site 2: personal_index/search_index.py SearchIndex._load
# ---------------------------------------------------------------------------
class TestSearchIndexStore:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-20: search_index.py SearchIndex._load crashes (AttributeError) "
        "on non-dict page value; contract (ARCH-63) requires empty state",
    )
    def test_non_dict_page_value_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "idx.json", {"pages": {"u": "notadict"}, "word_index": {}})
        idx = SearchIndexStore(index_path=p)
        assert idx.count() == 0
        assert idx.urls() == []

    def test_missing_file_yields_empty(self, tmp_path):
        idx = SearchIndexStore(index_path=str(tmp_path / "nope.json"))
        assert idx.count() == 0

    def test_non_dict_top_level_yields_empty(self, tmp_path):
        p = _write(tmp_path / "idx.json", "notadict")
        idx = SearchIndexStore(index_path=p)
        assert idx.count() == 0

    def test_valid_page_populates(self, tmp_path):
        p = _write(
            tmp_path / "idx.json",
            {"pages": {"http://x": {"url": "http://x", "title": "t"}}, "word_index": {}},
        )
        idx = SearchIndexStore(index_path=p)
        assert idx.count() == 1
        assert idx.get("http://x") is not None


# ---------------------------------------------------------------------------
# Site 3: personal_index/tags.py TagStore._load
# ---------------------------------------------------------------------------
class TestTagStore:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-20: tags.py TagStore._load crashes (AttributeError) on "
        "non-dict tag value; contract (ARCH-63) requires empty state",
    )
    def test_non_dict_tag_value_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "tags.json", {"tags": {"t": "notadict"}, "page_tags": {}})
        store = TagStore(store_path=p)
        assert store.list_tags() == []

    def test_missing_file_yields_empty(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "nope.json"))
        assert store.list_tags() == []

    def test_non_dict_top_level_yields_empty(self, tmp_path):
        p = _write(tmp_path / "tags.json", 42)
        store = TagStore(store_path=p)
        assert store.list_tags() == []

    def test_valid_tag_populates(self, tmp_path):
        p = _write(
            tmp_path / "tags.json",
            {"tags": {"t": {"color": "#fff", "description": "d"}}, "page_tags": {}},
        )
        store = TagStore(store_path=p)
        assert len(store.list_tags()) == 1
        assert store.get_tag("t") is not None


# ---------------------------------------------------------------------------
# Site 4: personal_index/interests.py InterestStore._load
# ---------------------------------------------------------------------------
class TestInterestStore:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-20: interests.py InterestStore._load crashes (AttributeError) "
        "on non-dict interest value; contract (ARCH-63) requires empty state",
    )
    def test_non_dict_interest_value_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "interests.json", {"i": "notadict"})
        store = InterestStore(store_path=p)
        assert store.list_all() == []

    def test_missing_file_yields_empty(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "nope.json"))
        assert store.list_all() == []

    def test_non_dict_top_level_yields_empty(self, tmp_path):
        p = _write(tmp_path / "interests.json", ["x"])
        store = InterestStore(store_path=p)
        assert store.list_all() == []

    def test_valid_interest_populates(self, tmp_path):
        p = _write(
            tmp_path / "interests.json",
            {"i": {"name": "i", "interest_type": "keyword", "keywords": ["k"]}},
        )
        store = InterestStore(store_path=p)
        assert len(store.list_all()) == 1
        assert store.get("i") is not None


# ---------------------------------------------------------------------------
# Site 5: personal_index/migrations/base.py MigrationStore._load
# ---------------------------------------------------------------------------
class TestMigrationStore:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-20: migrations/base.py MigrationStore._load crashes (TypeError) "
        "on non-dict migration record; contract (ARCH-63) requires empty state",
    )
    def test_non_dict_record_degrades_to_empty(self, tmp_path):
        p = _write(tmp_path / "mig.json", {"migrations": ["notadict"]})
        store = MigrationStore(store_path=p)
        assert store.get_applied_versions() == []

    def test_missing_file_yields_empty(self, tmp_path):
        store = MigrationStore(store_path=str(tmp_path / "nope.json"))
        assert store.get_applied_versions() == []

    def test_non_dict_top_level_yields_empty(self, tmp_path):
        p = _write(tmp_path / "mig.json", "notadict")
        store = MigrationStore(store_path=p)
        assert store.get_applied_versions() == []

    def test_valid_record_populates(self, tmp_path):
        p = _write(
            tmp_path / "mig.json",
            {"migrations": [{"name": "m", "version": 1}]},
        )
        store = MigrationStore(store_path=p)
        assert store.get_applied_versions() == [1]
        assert store.get_record(1) is not None


# ---------------------------------------------------------------------------
# Already-safe sites (clean armor): the guard already degrades to empty
# ---------------------------------------------------------------------------
class TestSafeSitesArmor:
    def test_content_versioning_non_dict_value_degrades(self, tmp_path):
        from personal_index.content_versioning import ContentVersioning

        p = _write(tmp_path / "cv.json", {"a": "notadict"})
        cv = ContentVersioning(storage_path=p)
        assert cv.get_versions("a") == []

    def test_content_versioning_valid_populates(self, tmp_path):
        from personal_index.content_versioning import ContentVersioning

        p = _write(
            tmp_path / "cv.json",
            {"a": [{"version_id": "v1", "content": "c"}]},
        )
        cv = ContentVersioning(storage_path=p)
        assert len(cv.get_versions("a")) == 1

    def test_domains_non_dict_value_degrades(self, tmp_path):
        from personal_index.domains import DomainManager

        p = _write(tmp_path / "dom.json", {"example.com": "notadict"})
        mgr = DomainManager(rules_file=p)
        assert mgr.list_rules() == []

    def test_domains_valid_populates(self, tmp_path):
        from personal_index.domains import DomainManager

        p = _write(
            tmp_path / "dom.json",
            {"example.com": {"domain": "example.com", "allowed": True}},
        )
        mgr = DomainManager(rules_file=p)
        assert len(mgr.list_rules()) == 1

    def test_scheduler_store_non_dict_value_degrades(self, tmp_path):
        from personal_index.scheduler import ScheduleStore

        p = _write(tmp_path / "sched.json", {"s": "notadict"})
        store = ScheduleStore(path=p)
        assert store.list_all() == []

    def test_scheduler_store_valid_populates(self, tmp_path):
        from personal_index.scheduler import ScheduleStore

        p = _write(
            tmp_path / "sched.json",
            {"s": {"config": {"interval_hours": 24}, "run_count": 0}},
        )
        store = ScheduleStore(path=p)
        assert len(store.list_all()) == 1

    def test_content_pin_non_dict_top_level_degrades(self, tmp_path):
        # content_pin non-dict VALUE crash is QA-17 (separate ticket); here we
        # pin the top-level guard that already works.
        from personal_index.content_pin import ContentPinner

        p = _write(tmp_path / "pin.json", ["not", "a", "dict"])
        pinner = ContentPinner(storage_path=p)
        assert pinner.get_pinned_items() == []


# ---------------------------------------------------------------------------
# End-to-end CLI: `health` must not crash on a malformed search_index.json
# ---------------------------------------------------------------------------
class TestCliHealthEndToEnd:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-20: `personal-index health` crashes (AttributeError) when "
        "search_index.json maps a page to a non-dict value; contract (ARCH-63) "
        "requires degrading to empty and reporting no indexed content",
    )
    def test_health_malformed_index_does_not_crash(self, tmp_path):
        from click.testing import CliRunner

        from personal_index.cli import main

        dd = str(tmp_path / "data")
        import os

        os.makedirs(dd, exist_ok=True)
        _write(os.path.join(dd, "search_index.json"),
               {"pages": {"u": "notadict"}, "word_index": {}})
        _write(os.path.join(dd, "tags.json"), {"tags": {}, "page_tags": {}})

        runner = CliRunner()
        result = runner.invoke(main, ["health", "--data-dir", dd])
        assert result.exit_code == 0, result.output
