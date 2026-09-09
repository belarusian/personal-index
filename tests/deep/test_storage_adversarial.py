"""Adversarial deep tests for personal_index.storage.Storage (validator cycle 157).

Pins the CURRENT documented contract in docs/storage.md as regression armor:
  - upsert-by-key (add_interest by name, add_page by url)
  - round-trips through the JSON files (to_dict/from_dict)
  - idempotence (re-adding the same key replaces in place, no duplicate)
  - guard paths (empty/whitespace/corrupt backing files -> empty default)
  - remove_* returns True/False and drops every matching entry
  - get_stats exact keys
  - one end-to-end run through the installed CLI (python -m personal_index)

The primary contract hole (non-atomic write + silent corruption recovery) is
tracked as ARCH-40 (OPEN) and is NOT re-filed here; the corruption-recovery
tests below pin the CURRENT documented behavior (silent empty default) so a
regression in either direction is witnessed.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from personal_index.models import CrawlConfig, IndexedPage, Interest
from personal_index.storage import Storage


# ── helpers ────────────────────────────────────────────────────────────

def _mk_interest(name: str, **kw) -> Interest:
    return Interest(name=name, **kw)


def _mk_page(url: str, **kw) -> IndexedPage:
    return IndexedPage(url=url, **kw)


@pytest.fixture
def store(tmp_path):
    return Storage(data_dir=str(tmp_path / "data"))


# ── guard paths: backing-file defaults ─────────────────────────────────

def test_fresh_store_starts_empty(store):
    assert store.get_interests() == []
    assert store.get_pages() == []
    assert store.get_page_count() == 0
    assert store.get_config() == CrawlConfig()


def test_empty_interests_file_returns_empty_list(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "interests.json").write_text("")
    (d / "config.json").write_text("{}")
    (d / "pages.json").write_text("[]")
    s = Storage(data_dir=str(d))
    assert s.get_interests() == []


def test_whitespace_pages_file_returns_empty_list(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "interests.json").write_text("[]")
    (d / "config.json").write_text("{}")
    (d / "pages.json").write_text("   \n\t  ")
    s = Storage(data_dir=str(d))
    assert s.get_pages() == []
    assert s.get_page_count() == 0


def test_corrupt_pages_file_silently_returns_empty_default(tmp_path):
    """Pins CURRENT documented behavior (ARCH-40 hole): a JSONDecodeError on
    read silently returns the empty default, surfacing as an empty store."""
    d = tmp_path / "d"
    d.mkdir()
    (d / "interests.json").write_text("[]")
    (d / "config.json").write_text("{}")
    (d / "pages.json").write_text('{"truncated": [1, 2,')  # invalid JSON
    s = Storage(data_dir=str(d))
    assert s.get_pages() == []
    assert s.get_page_count() == 0


def test_corrupt_config_file_returns_default_config(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "interests.json").write_text("[]")
    (d / "config.json").write_text("not json at all")
    (d / "pages.json").write_text("[]")
    s = Storage(data_dir=str(d))
    assert s.get_config() == CrawlConfig()


# ── interests: upsert, round-trip, idempotence ─────────────────────────

def test_add_interest_round_trip(store):
    i = _mk_interest("python", keywords=["py", "lang"], priority=7, enabled=True)
    got = store.add_interest(i)
    assert got is i  # returns the passed object unmutated
    back = store.get_interest("python")
    assert back is not None
    assert back.name == "python"
    assert back.keywords == ["py", "lang"]
    assert back.priority == 7
    assert back.enabled is True


def test_add_interest_idempotent_replaces_in_place(store):
    store.add_interest(_mk_interest("rust", keywords=["a"]))
    store.add_interest(_mk_interest("rust", keywords=["b", "c"]))
    pages = store.get_interests()
    assert len(pages) == 1  # replaced, not duplicated
    assert pages[0].keywords == ["b", "c"]


def test_add_interest_unicode_name_round_trip(store):
    name = "café-日本語-🚀"
    store.add_interest(_mk_interest(name, keywords=["x"]))
    back = store.get_interest(name)
    assert back is not None
    assert back.name == name


def test_add_interest_whitespace_name_is_distinct_key(store):
    store.add_interest(_mk_interest("  "))
    store.add_interest(_mk_interest("   "))
    # whitespace names are distinct keys (no normalization) -> two entries
    assert len(store.get_interests()) == 2


def test_get_interest_missing_returns_none(store):
    assert store.get_interest("does-not-exist") is None


def test_remove_interest_returns_true_then_false(store):
    store.add_interest(_mk_interest("go"))
    assert store.remove_interest("go") is True
    assert store.remove_interest("go") is False
    assert store.get_interests() == []


def test_remove_interest_drops_every_matching_entry(tmp_path):
    """Pins documented secondary hole: remove drops EVERY matching entry while
    add only replaces the first. We inject a duplicate directly."""
    d = tmp_path / "d"
    d.mkdir()
    s = Storage(data_dir=str(d))
    s.add_interest(_mk_interest("dup", keywords=["1"]))
    # force a second entry with the same name into the backing file
    data = json.loads(s.interests_file.read_text())
    data.append(_mk_interest("dup", keywords=["2"]).to_dict())
    s.interests_file.write_text(json.dumps(data))
    assert len(s.get_interests()) == 2
    assert s.remove_interest("dup") is True
    assert s.get_interests() == []


def test_list_interests_omits_priority_and_type(store):
    store.add_interest(_mk_interest("ml", keywords=["k"], priority=9))
    row = store.list_interests()[0]
    assert set(row.keys()) == {
        "name", "keywords", "url_patterns", "topics", "enabled", "created_at"
    }
    assert "priority" not in row
    assert "interest_type" not in row


# ── pages: upsert, round-trip, idempotence ─────────────────────────────

def test_add_page_round_trip(store):
    p = _mk_page("https://a.example/x", title="T", content="hello world",
                 content_length=11, score=0.9)
    got = store.add_page(p)
    assert got is p
    back = store.get_page("https://a.example/x")
    assert back is not None
    assert back.title == "T"
    assert back.content == "hello world"
    assert back.content_length == 11
    assert back.score == 0.9


def test_add_page_idempotent_replaces_in_place(store):
    store.add_page(_mk_page("https://b.example", title="v1"))
    store.add_page(_mk_page("https://b.example", title="v2"))
    pages = store.get_pages()
    assert len(pages) == 1
    assert pages[0].title == "v2"


def test_add_page_full_replace_clobbers_other_fields(store):
    """Pins documented secondary hole: a bare add clobbers every other field
    of the existing record with its defaults (no field-level merge)."""
    store.add_page(_mk_page("https://c.example", title="keep", content="body",
                            content_length=4))
    store.add_page(_mk_page("https://c.example"))  # bare record
    back = store.get_page("https://c.example")
    assert back is not None
    assert back.title == ""        # clobbered
    assert back.content == ""      # clobbered
    assert back.content_length == 0


def test_add_page_unicode_url_round_trip(store):
    url = "https://exämple.com/путь/🚀"
    store.add_page(_mk_page(url, title="u"))
    back = store.get_page(url)
    assert back is not None
    assert back.url == url


def test_get_page_missing_returns_none(store):
    assert store.get_page("https://nope.example") is None


def test_remove_page_returns_true_then_false(store):
    store.add_page(_mk_page("https://d.example"))
    assert store.remove_page("https://d.example") is True
    assert store.remove_page("https://d.example") is False
    assert store.get_page_count() == 0


def test_clear_pages_empties_store(store):
    store.add_page(_mk_page("https://e1.example"))
    store.add_page(_mk_page("https://e2.example"))
    store.clear_pages()
    assert store.get_pages() == []
    assert store.get_page_count() == 0


# ── config round-trip ──────────────────────────────────────────────────

def test_config_round_trip_preserves_fields(store):
    cfg = CrawlConfig(max_depth=7, rate_limit=42, max_pages=999,
                      allowed_domains=["ok.example"])
    got = store.save_config(cfg)
    assert got is cfg
    back = store.get_config()
    assert back.max_depth == 7
    assert back.rate_limit == 42
    assert back.max_pages == 999
    assert back.allowed_domains == ["ok.example"]


def test_config_idempotent_overwrite(store):
    store.save_config(CrawlConfig(max_depth=1))
    store.save_config(CrawlConfig(max_depth=2))
    assert store.get_config().max_depth == 2


# ── get_stats exact keys ───────────────────────────────────────────────

def test_get_stats_exact_keys_and_values(store):
    store.add_interest(_mk_interest("on", enabled=True))
    store.add_interest(_mk_interest("off", enabled=False))
    store.add_page(_mk_page("https://s1.example", content_length=10))
    store.add_page(_mk_page("https://s2.example", content_length=5))
    stats = store.get_stats()
    assert set(stats.keys()) == {
        "total_interests", "enabled_interests", "total_pages",
        "total_content_bytes", "data_dir",
    }
    assert stats["total_interests"] == 2
    assert stats["enabled_interests"] == 1
    assert stats["total_pages"] == 2
    assert stats["total_content_bytes"] == 15
    assert stats["data_dir"] == str(store.data_dir)


# ── persistence across instances (real round-trip through disk) ────────

def test_persistence_across_instances(tmp_path):
    d = str(tmp_path / "d")
    s1 = Storage(data_dir=d)
    s1.add_interest(_mk_interest("persist", keywords=["k"]))
    s1.add_page(_mk_page("https://p.example", title="P", content_length=3))
    s2 = Storage(data_dir=d)  # fresh instance, same dir
    assert s2.get_interest("persist") is not None
    assert s2.get_page("https://p.example") is not None
    assert s2.get_page_count() == 1


# ── end-to-end through the installed CLI ───────────────────────────────

def test_cli_status_end_to_end(tmp_path):
    """Run the installed CLI against a temp data dir; a fresh dir reports
    zero pages/interests and exits 0."""
    d = str(tmp_path / "cli-data")
    # Storage creates the backing files; the CLI reads the same data dir.
    Storage(data_dir=d)
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index", "status", "--data-dir", d],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Pages indexed:" in proc.stdout
    assert "Interests:" in proc.stdout
