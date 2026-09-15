"""Cycle 225 VERIFY: ARCH-71 — search_index.SearchIndex._save atomic + durable.

ARCH-71 (Issue #1403, umbrella ARCH-2 #983) pins that `_save` persists the
index **atomically and durably**: serialize to a temp file in the *same
directory* as `index_path`, `f.flush()` + `os.fsync(f.fileno())`, then
`os.replace(tmp, index_path)`. A crash mid-write must leave the prior complete
file intact — never a truncated document. The `_load` defensive degrade to `{}`
on a genuinely corrupt file (the *consequence* half) must remain unchanged.

These tests exercise the real `_save` entry point and assert the on-disk file
is always a complete, re-loadable document — pinning the contract against the
returned/reloaded object, not the docstring wording.

AC pinning (from the ticket):
  1. test_save_produces_complete_reloadable_file   (durability pin)
  2. test_save_empty_index_writes_valid_document   (empty-index guard)
  3. test_save_creates_missing_parent_dir          (regression guard)
  4. test_load_corrupt_file_still_degrades_to_empty (consequence-half pin)

Adversarial inputs the contract implies:
  - no leftover `.tmp` file after a save (os.replace consumed it)
  - idempotent re-save (save twice -> still complete, count unchanged)
  - save over a pre-existing valid file stays complete (os.replace, no truncation)
  - unicode content round-trips exactly through save/load
  - word index round-trips exactly (AC1 "matching word index")
"""

from __future__ import annotations

import json
import os

import pytest

from personal_index.models import CrawledPage
from personal_index.search_index import SearchIndex


def _page(url: str, title: str = "", content: str = "", rel: float = 0.0) -> CrawledPage:
    return CrawledPage(url=url, title=title, content=content, relevance_score=rel)


@pytest.fixture
def idx_path(tmp_path):
    return str(tmp_path / "search_index.json")


# ---------------------------------------------------------------------------
# AC pinning tests
# ---------------------------------------------------------------------------
class TestAtomicSaveAC:
    def test_save_produces_complete_reloadable_file(self, idx_path):
        """AC1: after a mutation that calls _save, the on-disk file is a
        complete, valid JSON document that a fresh SearchIndex reloads to the
        same page set and word index."""
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "Title A", "hello world"))

        # On-disk file exists and is parseable JSON.
        assert os.path.exists(idx_path)
        with open(idx_path, "r") as f:
            data = json.load(f)  # must not raise -> complete document

        # Document shape unchanged (AC6).
        assert set(data.keys()) == {"pages", "word_index"}
        assert set(data["pages"].keys()) == {"http://a"}

        # A fresh instance reloads to the same page set + matching word index.
        si2 = SearchIndex(idx_path)
        assert si2.count() == 1
        assert si2.urls() == ["http://a"]
        assert si2.get("http://a").title == "Title A"
        assert si2._word_index == si._word_index

    def test_save_empty_index_writes_valid_document(self, idx_path):
        """Guard path: a fresh index with no pages, then _save() -> the on-disk
        file is exactly {"pages": {}, "word_index": {}} (complete, valid,
        re-loadable)."""
        si = SearchIndex(idx_path)
        si._save()

        assert os.path.exists(idx_path)
        with open(idx_path, "r") as f:
            data = json.load(f)
        assert data == {"pages": {}, "word_index": {}}

        si2 = SearchIndex(idx_path)
        assert si2.count() == 0
        assert si2.urls() == []

    def test_save_creates_missing_parent_dir(self, tmp_path):
        """Regression guard: index_path in a not-yet-existing nested directory;
        _save() creates the parent (mkdir parents=True, exist_ok=True) and
        writes a re-loadable file."""
        nested = str(tmp_path / "a" / "b" / "c" / "idx.json")
        si = SearchIndex(nested)
        si.add(_page("http://a", "A", "x"))

        assert os.path.exists(nested)
        with open(nested, "r") as f:
            data = json.load(f)
        assert set(data["pages"].keys()) == {"http://a"}

        si2 = SearchIndex(nested)
        assert si2.count() == 1

    def test_load_corrupt_file_still_degrades_to_empty(self, idx_path):
        """Consequence-half pin (must remain true): a file pre-written with a
        truncated JSON prefix (the input the atomic _save is designed to never
        produce) -> a fresh SearchIndex degrades to an empty index."""
        with open(idx_path, "w") as f:
            f.write('{"pages": {"http://x": {"url": "http://x", "tit')

        si = SearchIndex(idx_path)
        assert si.count() == 0
        assert si.urls() == []


# ---------------------------------------------------------------------------
# Adversarial inputs the contract implies
# ---------------------------------------------------------------------------
class TestAtomicSaveAdversarial:
    def test_no_leftover_tmp_file_after_save(self, idx_path):
        """os.replace consumes the temp file: after a save there must be no
        stray `<index_path>.tmp` left in the directory."""
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "x"))

        tmp = idx_path + ".tmp"
        assert not os.path.exists(tmp)
        assert os.path.exists(idx_path)

    def test_idempotent_resave_stays_complete(self, idx_path):
        """Saving twice (idempotence) leaves a complete, re-loadable file with
        the same count — the second save atomically replaces the first."""
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        si._save()
        si._save()

        with open(idx_path, "r") as f:
            data = json.load(f)
        assert set(data["pages"].keys()) == {"http://a"}

        si2 = SearchIndex(idx_path)
        assert si2.count() == 1
        assert not os.path.exists(idx_path + ".tmp")

    def test_save_over_preexisting_file_stays_complete(self, idx_path):
        """os.replace over a pre-existing valid file: the constructor loads the
        old page into memory, the mutation adds a new one, and the resulting
        save is a complete document containing both (no partial merge, no
        truncation)."""
        with open(idx_path, "w") as f:
            json.dump({"pages": {"http://old": {"url": "http://old"}},
                       "word_index": {}}, f)

        si = SearchIndex(idx_path)  # loads http://old into memory
        si.add(_page("http://new", "New", "content here"))

        with open(idx_path, "r") as f:
            data = json.load(f)  # must be a complete document
        assert set(data["pages"].keys()) == {"http://old", "http://new"}

        si2 = SearchIndex(idx_path)
        assert si2.count() == 2
        assert set(si2.urls()) == {"http://old", "http://new"}

    def test_unicode_content_round_trips_exactly(self, idx_path):
        """Unicode content is persisted verbatim and reloaded byte-for-byte
        (the atomic write must not mangle non-ASCII bytes)."""
        si = SearchIndex(idx_path)
        si.add(_page("http://u", "Ünïcödé", "héllo wörld — 日本語"))

        si2 = SearchIndex(idx_path)
        assert si2.get("http://u").title == "Ünïcödé"
        assert si2.get("http://u").content == "héllo wörld — 日本語"

    def test_word_index_round_trips_exactly(self, idx_path):
        """AC1 'matching word index': the reloaded word index equals the
        in-memory word index token-for-token, url-for-url."""
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "Alpha", "shared token one"))
        si.add(_page("http://b", "Beta", "shared token two"))

        si2 = SearchIndex(idx_path)
        assert si2._word_index == si._word_index
        # A shared token maps to both urls.
        assert sorted(si2._word_index["shared"]) == ["http://a", "http://b"]
        assert sorted(si2._word_index["token"]) == ["http://a", "http://b"]
