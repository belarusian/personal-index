"""Cycle 190 PROBE: personal_index/search_index.py (live, never deep-tested).

`search_index.SearchIndex` is the CrawledPage-backed in-memory search index
used by `stats.py`, `scheduler.py` and `results.py` (distinct from the
IndexedPage-backed `index.SearchIndex` that the CLI uses). Its contract is its
own docstrings: `_tokenize` "removes punctuation", `search` "If limit <= 0,
returns an empty list", `remove` returns True/False, `_load` "Load index from
file".

Adversarial deep tests:
  - _tokenize: empty / whitespace / punctuation-only / unicode / mixed-case /
    digits / repeated tokens.
  - add: idempotence (same url twice), word_index dedup, empty url, empty
    title/content, unicode (tokenized to [] -> unsearchable, pinned as the
    actual behavior).
  - remove: present / absent / repeated / no-token page / shared-token
    consistency (removing one page must not drop another page's url from a
    shared token).
  - get / count / clear / urls: guard + ordering.
  - search: empty query, punctuation-only query, limit 0 / negative / 1 /
    large, scoring formula (title*3 + content*1 + relevance*0.5), ordering.
  - persistence: round-trip (add -> reload -> same count/title/search),
    crawled_at preserved across save/load, clear persists.

DEFECTS: none new. The defensive-load crash on a non-dict page value
(`_load` only catches `(json.JSONDecodeError, KeyError)`, so a `str` page
value raises AttributeError) is ALREADY filed as QA-20 (site 2 of the
ARCH-63 defensive-load-crash class sweep) — NOT re-filed here.
Unicode content is unsearchable because `_tokenize` uses `[a-z0-9]+`; the
docstring only promises "removing punctuation" (it does not promise unicode
support), so this is a design limitation, pinned as armor, not a defect.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.models import CrawledPage
from personal_index.search_index import SearchIndex


def _page(url: str, title: str = "", content: str = "", rel: float = 0.0) -> CrawledPage:
    return CrawledPage(url=url, title=title, content=content, relevance_score=rel)


@pytest.fixture
def idx_path(tmp_path):
    return str(tmp_path / "search_index.json")


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------
class TestTokenize:
    def test_empty_string(self):
        assert SearchIndex._tokenize("") == []

    def test_whitespace_only(self):
        assert SearchIndex._tokenize("   \t\n  ") == []

    def test_punctuation_only(self):
        assert SearchIndex._tokenize("!!! ??? ... ---") == []

    def test_lowercases(self):
        assert SearchIndex._tokenize("Hello World") == ["hello", "world"]

    def test_strips_punctuation(self):
        assert SearchIndex._tokenize("well-known, item.") == ["well", "known", "item"]

    def test_keeps_digits(self):
        assert SearchIndex._tokenize("python3 v2") == ["python3", "v2"]

    def test_repeated_tokens_preserved(self):
        # _tokenize does NOT dedup; dedup happens in add() via set(tokens)
        assert SearchIndex._tokenize("a a a") == ["a", "a", "a"]

    def test_unicode_dropped(self):
        # [a-z0-9]+ drops non-ASCII; docstring only promises punctuation removal
        assert SearchIndex._tokenize("Привет 日本語 中文") == []

    def test_mixed_ascii_and_unicode(self):
        assert SearchIndex._tokenize("hello Привет world") == ["hello", "world"]


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------
class TestAdd:
    def test_add_increments_count(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.count() == 1

    def test_add_idempotent_same_url(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello world"))
        si.add(_page("http://a", "A", "hello world"))
        assert si.count() == 1
        assert si._word_index.get("hello") == ["http://a"]

    def test_add_word_index_no_duplicate_url(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "foo bar foo"))
        assert si._word_index.get("foo") == ["http://a"]

    def test_add_empty_url(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("", "", ""))
        assert si.count() == 1
        assert si.urls() == [""]

    def test_add_empty_title_content(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://e", "", ""))
        assert si.count() == 1
        assert si.search("anything") == []

    def test_add_unicode_unsearchable(self, idx_path):
        # unicode tokens are dropped by _tokenize -> nothing indexed
        si = SearchIndex(idx_path)
        si.add(_page("http://u", "Привет мир", "日本語 content"))
        assert si.count() == 1
        assert si.search("привет") == []
        assert si.search("日本語") == []


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------
class TestRemove:
    def test_remove_present(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.remove("http://a") is True
        assert si.count() == 0

    def test_remove_absent(self, idx_path):
        si = SearchIndex(idx_path)
        assert si.remove("http://nope") is False

    def test_remove_repeated_returns_false(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.remove("http://a") is True
        assert si.remove("http://a") is False

    def test_remove_shared_token_keeps_other_page(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "world peace"))
        si.add(_page("http://b", "B", "world war"))
        assert si._word_index.get("world") == ["http://a", "http://b"]
        si.remove("http://a")
        assert si._word_index.get("world") == ["http://b"]

    def test_remove_deletes_empty_token(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "uniqueword"))
        assert "uniqueword" in si._word_index
        si.remove("http://a")
        assert "uniqueword" not in si._word_index

    def test_remove_no_token_page(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "", ""))
        assert si.remove("http://a") is True
        assert si.count() == 0


# ---------------------------------------------------------------------------
# get / count / clear / urls
# ---------------------------------------------------------------------------
class TestAccessors:
    def test_get_present(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "Title A", "content"))
        assert si.get("http://a").title == "Title A"

    def test_get_absent(self, idx_path):
        si = SearchIndex(idx_path)
        assert si.get("http://nope") is None

    def test_count_empty(self, idx_path):
        assert SearchIndex(idx_path).count() == 0

    def test_clear(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "x"))
        si.add(_page("http://b", "B", "y"))
        si.clear()
        assert si.count() == 0
        assert si.urls() == []
        assert si._word_index == {}

    def test_urls_order_insertion(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://1", "a", "x"))
        si.add(_page("http://2", "b", "y"))
        assert si.urls() == ["http://1", "http://2"]


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------
class TestSearch:
    def test_empty_query(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.search("") == []

    def test_punctuation_only_query(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.search("!!! ???") == []

    def test_limit_zero(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.search("hello", limit=0) == []

    def test_limit_negative(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.search("hello", limit=-1) == []

    def test_limit_one(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "python"))
        si.add(_page("http://b", "B", "python"))
        assert len(si.search("python", limit=1)) == 1

    def test_limit_larger_than_results(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "python"))
        assert len(si.search("python", limit=100)) == 1

    def test_scoring_formula(self, idx_path):
        # title_count*3 + content_count*1 + relevance*0.5
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "foo bar", "foo baz", rel=0.0))
        res = si.search("foo")
        assert res == [("http://a", 4.0)]

    def test_relevance_contribution(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "x", "y", rel=10.0))
        si.add(_page("http://b", "x", "y", rel=1.0))
        res = si.search("x")
        # title "x" has one "x" (3.0); content "y" has zero -> 3.0 + rel*0.5
        assert res == [("http://a", 8.0), ("http://b", 3.5)]

    def test_ordering_by_score_desc(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "python", "python python python"))
        si.add(_page("http://b", "python", "learn python"))
        res = si.search("python")
        assert res[0][0] == "http://a"
        assert res[0][1] > res[1][1]

    def test_no_match(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello"))
        assert si.search("zzz") == []


# ---------------------------------------------------------------------------
# persistence round-trip
# ---------------------------------------------------------------------------
class TestPersistence:
    def test_round_trip_count_and_title(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "Title A", "hello world"))
        si2 = SearchIndex(idx_path)
        assert si2.count() == 1
        assert si2.get("http://a").title == "Title A"

    def test_round_trip_search(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "hello world"))
        si2 = SearchIndex(idx_path)
        assert si2.search("hello") == [("http://a", 1.0)]

    def test_round_trip_crawled_at_preserved(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "x"))
        original = si.get("http://a").crawled_at
        si2 = SearchIndex(idx_path)
        assert si2.get("http://a").crawled_at == original

    def test_clear_persists(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "x"))
        si.clear()
        si2 = SearchIndex(idx_path)
        assert si2.count() == 0

    def test_remove_persists(self, idx_path):
        si = SearchIndex(idx_path)
        si.add(_page("http://a", "A", "x"))
        si.add(_page("http://b", "B", "y"))
        si.remove("http://a")
        si2 = SearchIndex(idx_path)
        assert si2.count() == 1
        assert si2.urls() == ["http://b"]

    def test_missing_file_yields_empty(self, tmp_path):
        si = SearchIndex(str(tmp_path / "does_not_exist.json"))
        assert si.count() == 0
        assert si.urls() == []


# ---------------------------------------------------------------------------
# End-to-end CLI smoke run (installed CLI still boots)
# ---------------------------------------------------------------------------
class TestCliSmoke:
    def test_cli_version_runs(self):
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
        assert "version" in proc.stdout.lower()
