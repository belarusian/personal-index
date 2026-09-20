"""Adversarial deep tests for personal_index.cli_dedup + content_dedup engine.

Cycle 220 — VALIDATOR probe of a never-probed subsystem (cli_dedup).

cli_dedup is the `personal-index dedup` CLI command; it is a thin wrapper over
the ContentDeduplicator engine (personal_index/content_dedup.py). The contract
is pinned from docs/dedup.md + the engine docstrings:

- normalize_url: empty returned unchanged; fragment removed; trailing slash
  stripped (lone root "/" preserved); scheme+host lowercased, path byte-for-byte.
- content_hash: empty -> ""; else sha256 of (lowercase, strip, collapse
  whitespace) -> 64 hex chars.
- DocumentHash.compute_fingerprint: first 16 chars of content_hash; empty -> "".
- url_hash: sha256(normalize_url(url)) -> 64 chars even for empty url.
- text_similarity: falsy either side -> 0.0; no [a-z0-9]+ tokens -> 0.0; else
  Jaccard of word sets.
- DedupResult.dedup_ratio: 0.0 when total_items==0, else removed/total.
- DedupResult.summary: exactly 7 lines in fixed order.
- DuplicateGroup.total_count = 1 + len(duplicates); to_dict round-trip.
- dedup_by_hash: empty content skipped (never grouped); >1-item group ->
  representative=first url, duplicates=rest, score 1.0, method "exact_hash".
- dedup_by_url: empty normalized url skipped; >1-item group -> method
  "normalized_url", score 1.0.
- dedup_by_similarity: threshold-gated Jaccard; empty content never groups.
- dedup_all: url -> hash -> similarity pipeline; combined groups + summed
  removed_count; method "combined".
- CLI helpers: _build_dedup_items (content None -> ""), _dispatch_dedup.
- CLI end-to-end: empty index, dry-run (no removal), remove (persisted),
  method choices, similarity threshold.

The negative-slice "top N" CLASS SWEEP for this cycle found ONE new public
site (keyword_extractor.extract(limit=-1)); it is pinned in
test_keyword_extractor_adversarial.py and filed as QA-37 — NOT here.
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.cli_dedup import (
    _build_dedup_items,
    _dispatch_dedup,
    _load_indexed_content,
)
from personal_index.content_dedup import (
    ContentDeduplicator,
    DedupResult,
    DocumentHash,
    DuplicateGroup,
    content_hash,
    normalize_url,
    text_similarity,
    url_hash,
)
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------
class TestNormalizeUrl:
    def test_empty_returned_unchanged(self):
        assert normalize_url("") == ""

    def test_fragment_removed(self):
        assert normalize_url("http://a.com/x#frag") == "http://a.com/x"

    def test_trailing_slash_stripped(self):
        assert normalize_url("http://a.com/x/") == "http://a.com/x"

    def test_multiple_trailing_slashes_stripped(self):
        assert normalize_url("http://a.com/x///") == "http://a.com/x"

    def test_lone_root_slash_preserved(self):
        # A lone "/" must NOT be stripped to "" (len>1 guard).
        assert normalize_url("/") == "/"

    def test_scheme_host_lowercased_path_preserved(self):
        assert normalize_url("HTTP://A.COM/Path/Case") == "http://a.com/Path/Case"

    def test_host_only_lowercased(self):
        assert normalize_url("HTTPS://A.COM") == "https://a.com"

    def test_no_scheme_only_fragment_and_slash(self):
        # No "://" separator -> only steps (1) and (2).
        assert normalize_url("a.com/x/#f/") == "a.com/x"

    def test_fragment_then_trailing_slash(self):
        # Fragment removed first, then trailing slash of the remainder.
        assert normalize_url("http://a.com/x/#f") == "http://a.com/x"

    def test_idempotent(self):
        u = "HTTP://A.COM/Path/"
        assert normalize_url(normalize_url(u)) == normalize_url(u)


# ---------------------------------------------------------------------------
# content_hash / DocumentHash / url_hash
# ---------------------------------------------------------------------------
class TestHashing:
    def test_content_hash_empty(self):
        assert content_hash("") == ""

    def test_content_hash_64_hex(self):
        h = content_hash("hello world")
        assert len(h) == 64
        int(h, 16)  # valid hex

    def test_content_hash_case_insensitive(self):
        assert content_hash("Hello World") == content_hash("hello world")

    def test_content_hash_whitespace_collapsed(self):
        assert content_hash("a   b\n\tc") == content_hash("a b c")

    def test_content_hash_strips_edges(self):
        assert content_hash("  hello  ") == content_hash("hello")

    def test_content_hash_unicode(self):
        assert content_hash("héllo wörld") == content_hash("héllo wörld")
        assert len(content_hash("héllo wörld")) == 64

    def test_fingerprint_16_chars(self):
        fp = DocumentHash.compute_fingerprint("some content here")
        assert len(fp) == 16
        assert fp == content_hash("some content here")[:16]

    def test_fingerprint_empty(self):
        assert DocumentHash.compute_fingerprint("") == ""

    def test_url_hash_64_chars(self):
        assert len(url_hash("http://a.com/x")) == 64

    def test_url_hash_empty_still_hashed(self):
        # Empty url normalizes to "" but is still hashed (no guard).
        assert len(url_hash("")) == 64

    def test_url_hash_normalizes(self):
        assert url_hash("HTTP://A.COM/x/") == url_hash("http://a.com/x")


# ---------------------------------------------------------------------------
# text_similarity
# ---------------------------------------------------------------------------
class TestTextSimilarity:
    def test_empty_either_side_zero(self):
        assert text_similarity("", "abc") == 0.0
        assert text_similarity("abc", "") == 0.0

    def test_no_tokens_zero(self):
        assert text_similarity("!!! ???", "abc") == 0.0

    def test_identical_one(self):
        assert text_similarity("the quick brown fox", "the quick brown fox") == 1.0

    def test_disjoint_zero(self):
        assert text_similarity("apple banana", "cherry date") == 0.0

    def test_partial_jaccard(self):
        # {a,b} vs {b,c}: inter=1, union=3 -> 1/3
        assert text_similarity("a b", "b c") == pytest.approx(1 / 3)

    def test_case_insensitive(self):
        assert text_similarity("Hello World", "hello world") == 1.0

    def test_symmetric(self):
        assert text_similarity("a b c", "b c d") == text_similarity("b c d", "a b c")


# ---------------------------------------------------------------------------
# DedupResult / DuplicateGroup
# ---------------------------------------------------------------------------
class TestDedupResult:
    def test_ratio_zero_when_no_items(self):
        assert DedupResult(total_items=0, removed_count=0).dedup_ratio == 0.0

    def test_ratio_computed(self):
        r = DedupResult(total_items=4, removed_count=2)
        assert r.dedup_ratio == pytest.approx(0.5)

    def test_summary_seven_lines(self):
        r = DedupResult(
            total_items=5, unique_items=3, removed_count=2,
            duplicate_groups=[DuplicateGroup(representative="u")],
            method="hash",
        )
        lines = r.summary().split("\n")
        assert len(lines) == 7
        assert lines[0] == "Deduplication Results:"
        assert lines[1] == "  Total items: 5"
        assert lines[2] == "  Unique items: 3"
        assert lines[3] == "  Duplicates found: 2"
        assert lines[4] == "  Duplicate groups: 1"
        assert lines[5] == "  Dedup ratio: 40.0%"
        assert lines[6] == "  Method: hash"

    def test_summary_zero_items_renders_zero(self):
        lines = DedupResult().summary().split("\n")
        assert lines[1] == "  Total items: 0"
        assert lines[5] == "  Dedup ratio: 0.0%"


class TestDuplicateGroup:
    def test_total_count(self):
        g = DuplicateGroup(representative="u", duplicates=["a", "b"])
        assert g.total_count == 3

    def test_total_count_no_dups(self):
        assert DuplicateGroup(representative="u").total_count == 1

    def test_to_dict_round_trip(self):
        g = DuplicateGroup(
            representative="u", duplicates=["a"],
            similarity_score=0.9, dedup_method="similarity",
        )
        d = g.to_dict()
        assert d == {
            "representative": "u", "duplicates": ["a"],
            "similarity_score": 0.9, "dedup_method": "similarity",
            "total_count": 2,
        }


# ---------------------------------------------------------------------------
# dedup_by_hash
# ---------------------------------------------------------------------------
class TestDedupByHash:
    def test_empty_content_skipped(self):
        d = ContentDeduplicator()
        items = [
            {"url": "u1", "content": ""},
            {"url": "u2", "content": ""},
        ]
        r = d.dedup_by_hash(items)
        assert r.duplicate_groups == []
        assert r.removed_count == 0
        assert r.method == "hash"

    def test_exact_group(self):
        d = ContentDeduplicator()
        items = [
            {"url": "u1", "content": "same body"},
            {"url": "u2", "content": "same body"},
            {"url": "u3", "content": "same body"},
        ]
        r = d.dedup_by_hash(items)
        assert len(r.duplicate_groups) == 1
        g = r.duplicate_groups[0]
        assert g.representative == "u1"
        assert g.duplicates == ["u2", "u3"]
        assert g.similarity_score == 1.0
        assert g.dedup_method == "exact_hash"
        assert r.removed_count == 2
        assert r.total_items == 3
        assert r.unique_items == 1

    def test_whitespace_insensitive_grouping(self):
        d = ContentDeduplicator()
        items = [
            {"url": "u1", "content": "  Hello   World  "},
            {"url": "u2", "content": "hello world"},
        ]
        r = d.dedup_by_hash(items)
        assert len(r.duplicate_groups) == 1

    def test_all_unique(self):
        d = ContentDeduplicator()
        items = [{"url": f"u{i}", "content": f"body {i}"} for i in range(3)]
        r = d.dedup_by_hash(items)
        assert r.duplicate_groups == []
        assert r.removed_count == 0
        assert r.unique_items == 3

    def test_empty_items(self):
        r = ContentDeduplicator().dedup_by_hash([])
        assert r.total_items == 0
        assert r.duplicate_groups == []

    def test_custom_hash_field(self):
        d = ContentDeduplicator()
        items = [
            {"url": "u1", "content": "a", "title": "T"},
            {"url": "u2", "content": "b", "title": "T"},
        ]
        r = d.dedup_by_hash(items, hash_field="title")
        assert len(r.duplicate_groups) == 1


# ---------------------------------------------------------------------------
# dedup_by_url
# ---------------------------------------------------------------------------
class TestDedupByUrl:
    def test_empty_url_skipped(self):
        d = ContentDeduplicator()
        items = [{"url": "", "content": "a"}, {"url": "", "content": "b"}]
        r = d.dedup_by_url(items)
        assert r.duplicate_groups == []
        assert r.removed_count == 0

    def test_normalized_grouping(self):
        d = ContentDeduplicator()
        items = [
            {"url": "http://a.com/x/", "content": "a"},
            {"url": "http://a.com/x", "content": "b"},
            {"url": "HTTP://A.COM/x#frag", "content": "c"},
        ]
        r = d.dedup_by_url(items)
        assert len(r.duplicate_groups) == 1
        g = r.duplicate_groups[0]
        assert g.representative == "http://a.com/x/"
        assert g.duplicates == ["http://a.com/x", "HTTP://A.COM/x#frag"]
        assert g.dedup_method == "normalized_url"
        assert g.similarity_score == 1.0
        assert r.removed_count == 2

    def test_distinct_urls_no_group(self):
        d = ContentDeduplicator()
        items = [{"url": "http://a.com/1"}, {"url": "http://a.com/2"}]
        r = d.dedup_by_url(items)
        assert r.duplicate_groups == []

    def test_method_is_url(self):
        assert ContentDeduplicator().dedup_by_url([]).method == "url"


# ---------------------------------------------------------------------------
# dedup_by_similarity
# ---------------------------------------------------------------------------
class TestDedupBySimilarity:
    def test_identical_grouped(self):
        d = ContentDeduplicator(similarity_threshold=0.9)
        items = [
            {"url": "u1", "content": "the quick brown fox jumps"},
            {"url": "u2", "content": "the quick brown fox jumps"},
        ]
        r = d.dedup_by_similarity(items)
        assert len(r.duplicate_groups) == 1
        assert r.duplicate_groups[0].dedup_method == "similarity"
        assert r.removed_count == 1

    def test_below_threshold_not_grouped(self):
        d = ContentDeduplicator(similarity_threshold=0.9)
        items = [
            {"url": "u1", "content": "alpha beta gamma delta"},
            {"url": "u2", "content": "epsilon zeta eta theta"},
        ]
        r = d.dedup_by_similarity(items)
        assert r.duplicate_groups == []

    def test_empty_content_never_groups(self):
        d = ContentDeduplicator(similarity_threshold=0.1)
        items = [{"url": "u1", "content": ""}, {"url": "u2", "content": ""}]
        r = d.dedup_by_similarity(items)
        assert r.duplicate_groups == []

    def test_score_is_threshold(self):
        d = ContentDeduplicator(similarity_threshold=0.5)
        items = [
            {"url": "u1", "content": "one two three four"},
            {"url": "u2", "content": "one two three four"},
        ]
        r = d.dedup_by_similarity(items)
        assert r.duplicate_groups[0].similarity_score == 0.5

    def test_method_is_similarity(self):
        assert ContentDeduplicator().dedup_by_similarity([]).method == "similarity"


# ---------------------------------------------------------------------------
# dedup_all (combined pipeline)
# ---------------------------------------------------------------------------
class TestDedupAll:
    def test_combined_method(self):
        r = ContentDeduplicator().dedup_all([])
        assert r.method == "combined"

    def test_url_and_hash_both_caught(self):
        d = ContentDeduplicator()
        items = [
            # url dup
            {"url": "http://a.com/x/", "content": "unique one"},
            {"url": "http://a.com/x", "content": "unique two"},
            # hash dup (different urls, same content)
            {"url": "http://b.com/1", "content": "shared body"},
            {"url": "http://b.com/2", "content": "shared body"},
        ]
        r = d.dedup_all(items)
        assert r.total_items == 4
        assert r.removed_count == 2
        methods = {g.dedup_method for g in r.duplicate_groups}
        assert "normalized_url" in methods
        assert "exact_hash" in methods

    def test_unique_items_consistent(self):
        d = ContentDeduplicator()
        items = [
            {"url": "u1", "content": "a"},
            {"url": "u2", "content": "a"},
            {"url": "u3", "content": "b"},
        ]
        r = d.dedup_all(items)
        assert r.unique_items == r.total_items - r.removed_count


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------
class TestCliHelpers:
    def test_build_dedup_items_content_none_to_empty(self):
        class P:
            url = "u"
            title = "t"
            content = None
        items = _build_dedup_items([P()])
        assert items == [{"url": "u", "title": "t", "content": ""}]

    def test_build_dedup_items_content_preserved(self):
        class P:
            url = "u"
            title = "t"
            content = "body"
        items = _build_dedup_items([P()])
        assert items[0]["content"] == "body"

    def test_dispatch_hash(self):
        items = [{"url": "u1", "content": "x"}, {"url": "u2", "content": "x"}]
        r = _dispatch_dedup(items, "hash", 0.9)
        assert r.method == "hash"

    def test_dispatch_url(self):
        r = _dispatch_dedup([], "url", 0.9)
        assert r.method == "url"

    def test_dispatch_similarity(self):
        r = _dispatch_dedup([], "similarity", 0.9)
        assert r.method == "similarity"

    def test_dispatch_all(self):
        r = _dispatch_dedup([], "all", 0.9)
        assert r.method == "combined"

    def test_load_indexed_content_empty(self, tmp_path):
        pages, idx = _load_indexed_content(str(tmp_path))
        assert pages == []
        assert idx.get_page_count() == 0


# ---------------------------------------------------------------------------
# CLI end-to-end (installed entry point)
# ---------------------------------------------------------------------------
def _seed(dd, pages):
    idx = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    for url, title, content in pages:
        idx.add_page(IndexedPage(url=url, title=title, content=content))
    return idx


class TestCliEndToEnd:
    def test_empty_index(self, tmp_path):
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, ["dedup", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "No indexed content found." in r.output

    def test_dry_run_no_removal(self, tmp_path):
        _seed(str(tmp_path), [
            ("http://a.com/1", "A1", "hello world body"),
            ("http://a.com/2", "A2", "hello world body"),
        ])
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, ["dedup", "--data-dir", str(tmp_path), "--dry-run"])
        assert r.exit_code == 0
        assert "(Dry run - no changes made)" in r.output
        idx = SearchIndex(db_path=os.path.join(str(tmp_path), "search_index.json"))
        assert idx.get_page_count() == 2

    def test_remove_persists(self, tmp_path):
        _seed(str(tmp_path), [
            ("http://a.com/1", "A1", "hello world body"),
            ("http://a.com/2", "A2", "hello world body"),
            ("http://b.com/3", "B", "unique content"),
        ])
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, ["dedup", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "Removed 1 duplicate pages." in r.output
        idx = SearchIndex(db_path=os.path.join(str(tmp_path), "search_index.json"))
        assert idx.get_page_count() == 2
        urls = {p.url for p in idx.list_pages()}
        assert "http://a.com/2" not in urls  # duplicate removed
        assert "http://a.com/1" in urls  # representative kept

    def test_no_duplicates(self, tmp_path):
        _seed(str(tmp_path), [
            ("http://a.com/1", "A1", "one"),
            ("http://b.com/2", "B2", "two"),
        ])
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, ["dedup", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "No duplicates found!" in r.output

    def test_method_hash_only(self, tmp_path):
        # url-normalized dup but distinct content: hash method must NOT catch it
        _seed(str(tmp_path), [
            ("http://a.com/x/", "A", "content one"),
            ("http://a.com/x", "B", "content two"),
        ])
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, ["dedup", "--data-dir", str(tmp_path), "-m", "hash"])
        assert r.exit_code == 0
        assert "No duplicates found!" in r.output

    def test_method_url_only(self, tmp_path):
        # same content, distinct urls: url method must NOT catch it
        _seed(str(tmp_path), [
            ("http://a.com/1", "A", "same body"),
            ("http://b.com/2", "B", "same body"),
        ])
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, ["dedup", "--data-dir", str(tmp_path), "-m", "url"])
        assert r.exit_code == 0
        assert "No duplicates found!" in r.output

    def test_invalid_method_rejected(self, tmp_path):
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, ["dedup", "--data-dir", str(tmp_path), "-m", "bogus"])
        assert r.exit_code != 0

    def test_similarity_threshold_flag(self, tmp_path):
        # near-dup: identical content, threshold 0.8 catches it
        _seed(str(tmp_path), [
            ("http://a.com/1", "A", "the quick brown fox jumps over"),
            ("http://b.com/2", "B", "the quick brown fox jumps over"),
        ])
        runner = CliRunner(isolate_filesystem=False)
        r = runner.invoke(main, [
            "dedup", "--data-dir", str(tmp_path),
            "-m", "similarity", "--similarity-threshold", "0.8",
        ])
        assert r.exit_code == 0
        assert "Duplicates found: 1" in r.output
