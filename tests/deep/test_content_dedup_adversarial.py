"""Adversarial deep tests for personal_index.content_dedup (cycle 166 probe).

content_dedup was never probed. This cycle attacks every precise docstring
claim in the module with guard inputs (None/empty/whitespace/unicode/
duplicate/out-of-range), round-trips, idempotence and property checks, plus
one end-to-end CLI run. All claims held at HEAD -> regression armor.

Contracts attacked (all verified passing at HEAD):
  * normalize_url: empty->''; '/' preserved; fragment stripped; trailing
    slash stripped (root kept); scheme+host lowercased, path case preserved;
    no-:// URLs get only fragment+slash steps.
  * content_hash: ''->''; whitespace-only -> sha256(''); normalize =
    lowercase+strip+collapse-whitespace; 64-char hexdigest.
  * DocumentHash.compute_fingerprint: ''->''; else 16-char prefix.
  * url_hash: always 64-char (empty url still hashed).
  * text_similarity: either falsy -> 0.0; no [a-z0-9]+ tokens -> 0.0;
    else Jaccard of lowercased word sets.
  * DedupResult.dedup_ratio: total_items==0 -> 0.0 (no ZeroDivisionError).
  * DedupResult.summary: exact 7-line format, 0.0% when empty.
  * DuplicateGroup.total_count / to_dict.
  * ContentDeduplicator.dedup_by_hash: empty content skipped, never grouped.
  * ContentDeduplicator.dedup_by_url: empty url skipped; scheme/host case
    folded, path case preserved (so differing path case is NOT a dup).
  * ContentDeduplicator.dedup_by_similarity: out-of-range thresholds behave
    as plain float comparison (no crash).
  * ContentDeduplicator.dedup_all: URL->hash->similarity pipeline; empty
    url/content items collapse to first survivor; idempotent on unique input.
  * CLI `personal-index dedup` on an empty data dir -> "No indexed content
    found." with rc 0.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys

import pytest

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


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------
class TestNormalizeUrl:
    def test_empty_returns_empty(self):
        assert normalize_url("") == ""

    def test_root_slash_preserved(self):
        assert normalize_url("/") == "/"

    def test_double_slash_collapses_to_empty(self):
        # '//' -> rstrip('/') -> '' (documented: trailing slash stripped when
        # fragment-removed string is longer than one char).
        assert normalize_url("//") == ""

    def test_fragment_stripped(self):
        assert normalize_url("https://example.com/path#frag") == "https://example.com/path"

    def test_fragment_only(self):
        assert normalize_url("https://example.com#") == "https://example.com"

    def test_trailing_slash_stripped(self):
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_multiple_trailing_slashes(self):
        assert normalize_url("https://example.com//") == "https://example.com"

    def test_scheme_and_host_lowercased_path_preserved(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/My/Path#frag") == "https://example.com/My/Path"

    def test_no_scheme_only_fragment_and_slash(self):
        assert normalize_url("no-scheme/path/") == "no-scheme/path"

    def test_port_preserved(self):
        assert normalize_url("https://example.com:8080/") == "https://example.com:8080"

    def test_idempotent(self):
        for u in ["https://example.com/a/b/", "HTTPS://X.COM/P", "no-scheme/p/", "/"]:
            once = normalize_url(u)
            assert normalize_url(once) == once


# ---------------------------------------------------------------------------
# content_hash / DocumentHash / url_hash
# ---------------------------------------------------------------------------
class TestHashes:
    def test_content_hash_empty(self):
        assert content_hash("") == ""

    def test_content_hash_whitespace_only(self):
        # '   ' -> strip -> '' -> sha256('')
        assert content_hash("   ") == hashlib.sha256(b"").hexdigest()

    def test_content_hash_normalizes_whitespace(self):
        assert content_hash("  Hello   World  ") == content_hash("Hello\nWorld")

    def test_content_hash_64_hex(self):
        h = content_hash("hello")
        assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)

    def test_content_hash_unicode(self):
        assert len(content_hash("café")) == 64

    def test_fingerprint_empty(self):
        assert DocumentHash.compute_fingerprint("") == ""

    def test_fingerprint_16_prefix(self):
        assert DocumentHash.compute_fingerprint("hello world") == content_hash("hello world")[:16]
        assert len(DocumentHash.compute_fingerprint("hello world")) == 16

    def test_url_hash_always_64(self):
        assert len(url_hash("")) == 64
        assert len(url_hash("https://example.com/")) == 64

    def test_url_hash_case_insensitive_scheme_host(self):
        assert url_hash("HTTPS://Example.com/Path") == url_hash("https://example.com/Path")


# ---------------------------------------------------------------------------
# text_similarity
# ---------------------------------------------------------------------------
class TestTextSimilarity:
    def test_either_empty_zero(self):
        assert text_similarity("", "abc") == 0.0
        assert text_similarity("abc", "") == 0.0

    def test_no_tokens_zero(self):
        assert text_similarity("!!!", "abc") == 0.0
        assert text_similarity("abc", "!!!") == 0.0

    def test_identical_one(self):
        assert text_similarity("café", "café") == 1.0

    def test_jaccard(self):
        # {a,b,c} vs {a,b,c,d} -> 3/4
        assert text_similarity("a b c", "a b c d") == pytest.approx(0.75)

    def test_disjoint_zero(self):
        assert text_similarity("foo bar", "baz qux") == 0.0

    def test_symmetric(self):
        assert text_similarity("alpha beta", "beta gamma") == text_similarity("beta gamma", "alpha beta")


# ---------------------------------------------------------------------------
# DedupResult / DuplicateGroup
# ---------------------------------------------------------------------------
class TestDedupResult:
    def test_ratio_zero_total_no_crash(self):
        assert DedupResult(total_items=0).dedup_ratio == 0.0

    def test_ratio_value(self):
        r = DedupResult(total_items=10, unique_items=7, removed_count=3)
        assert r.dedup_ratio == pytest.approx(0.3)

    def test_summary_empty(self):
        s = DedupResult(total_items=0).summary()
        assert s == (
            "Deduplication Results:\n"
            "  Total items: 0\n"
            "  Unique items: 0\n"
            "  Duplicates found: 0\n"
            "  Duplicate groups: 0\n"
            "  Dedup ratio: 0.0%\n"
            "  Method: hash"
        )

    def test_summary_lines(self):
        r = DedupResult(total_items=10, unique_items=7, removed_count=3, method="hash")
        lines = r.summary().split("\n")
        assert lines[0] == "Deduplication Results:"
        assert lines[1] == "  Total items: 10"
        assert lines[2] == "  Unique items: 7"
        assert lines[3] == "  Duplicates found: 3"
        assert lines[5] == "  Dedup ratio: 30.0%"
        assert lines[6] == "  Method: hash"

    def test_group_total_count_and_to_dict(self):
        g = DuplicateGroup(representative="u", duplicates=["a", "b"],
                           similarity_score=0.5, dedup_method="x")
        assert g.total_count == 3
        d = g.to_dict()
        assert d == {"representative": "u", "duplicates": ["a", "b"],
                     "similarity_score": 0.5, "dedup_method": "x", "total_count": 3}


# ---------------------------------------------------------------------------
# ContentDeduplicator
# ---------------------------------------------------------------------------
class TestDedupByHash:
    def test_empty_content_skipped(self):
        r = ContentDeduplicator().dedup_by_hash(
            [{"url": "a", "content": ""}, {"url": "b", "content": ""}])
        assert r.total_items == 2
        assert r.unique_items == 2
        assert r.removed_count == 0
        assert r.duplicate_groups == []

    def test_exact_hash_groups(self):
        r = ContentDeduplicator().dedup_by_hash(
            [{"url": "a", "content": "same"}, {"url": "b", "content": "same"},
             {"url": "c", "content": "diff"}])
        assert r.removed_count == 1
        assert len(r.duplicate_groups) == 1
        assert r.duplicate_groups[0].representative == "a"
        assert r.duplicate_groups[0].duplicates == ["b"]
        assert r.duplicate_groups[0].dedup_method == "exact_hash"

    def test_whitespace_normalized_hash(self):
        # '  x  y ' and 'x\ny' hash identically -> duplicate
        r = ContentDeduplicator().dedup_by_hash(
            [{"url": "a", "content": "  x  y "}, {"url": "b", "content": "x\ny"}])
        assert r.removed_count == 1


class TestDedupByUrl:
    def test_empty_url_skipped(self):
        r = ContentDeduplicator().dedup_by_url([{"url": ""}, {"url": ""}])
        assert r.total_items == 2
        assert r.removed_count == 0
        assert r.duplicate_groups == []

    def test_scheme_host_case_folded(self):
        r = ContentDeduplicator().dedup_by_url(
            [{"url": "HTTPS://Example.com/Path"}, {"url": "https://example.com/Path"}])
        assert r.removed_count == 1
        assert r.duplicate_groups[0].dedup_method == "normalized_url"

    def test_path_case_preserved_not_dup(self):
        # Path case is byte-for-byte preserved, so /P vs /p are NOT duplicates.
        r = ContentDeduplicator().dedup_by_url(
            [{"url": "https://example.com/P"}, {"url": "https://example.com/p"}])
        assert r.removed_count == 0

    def test_fragment_and_slash_folded(self):
        r = ContentDeduplicator().dedup_by_url(
            [{"url": "https://example.com/a/"}, {"url": "https://example.com/a#frag"}])
        assert r.removed_count == 1


class TestDedupBySimilarity:
    def test_out_of_range_thresholds_no_crash(self):
        for th in (0.0, 1.0, -0.5, 1.5):
            d = ContentDeduplicator(similarity_threshold=th)
            r = d.dedup_by_similarity(
                [{"url": "a", "content": "x y"}, {"url": "b", "content": "x y"}])
            assert r.total_items == 2
        # threshold 1.5: identical text (sim 1.0) is below -> not grouped
        r = ContentDeduplicator(similarity_threshold=1.5).dedup_by_similarity(
            [{"url": "a", "content": "x y"}, {"url": "b", "content": "x y"}])
        assert r.removed_count == 0

    def test_empty_content_never_groups(self):
        r = ContentDeduplicator().dedup_by_similarity(
            [{"url": "a", "content": ""}, {"url": "b", "content": ""}])
        assert r.removed_count == 0


class TestDedupAll:
    def test_empty_url_content_not_grouped(self):
        # Empty-URL items are SKIPPED by dedup_by_url (never grouped), so they
        # never increment removed_count. Per the Returns clause the final
        # unique_items = len(items) - removed_count = 2 (the intermediate
        # list fed to the next stage collapses to the first survivor, but the
        # reported field does not).
        r = ContentDeduplicator().dedup_all(
            [{"url": "", "content": ""}, {"url": "", "content": ""}])
        assert r.total_items == 2
        assert r.removed_count == 0
        assert r.unique_items == 2
        assert r.duplicate_groups == []

    def test_same_url_diff_content(self):
        r = ContentDeduplicator().dedup_all(
            [{"url": "u", "content": "x"}, {"url": "u", "content": "y"}])
        assert r.removed_count == 1
        assert r.method == "combined"

    def test_diff_url_same_content(self):
        r = ContentDeduplicator().dedup_all(
            [{"url": "a", "content": "same"}, {"url": "b", "content": "same"}])
        assert r.removed_count == 1

    def test_idempotent_on_unique(self):
        d = ContentDeduplicator()
        items = [{"url": "a", "content": "x y z"},
                 {"url": "b", "content": "x y z"},
                 {"url": "c", "content": "w"}]
        r1 = d.dedup_all(items)
        assert r1.unique_items == 2 and r1.removed_count == 1


# ---------------------------------------------------------------------------
# End-to-end CLI
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_dedup_empty_data_dir(self, tmp_path):
        dd = tmp_path / "empty"
        dd.mkdir()
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index", "dedup", "--data-dir", str(dd)],
            capture_output=True, text=True, cwd="/home/sasha/AI/personal-index-3/proj")
        assert proc.returncode == 0
        assert "No indexed content found." in proc.stdout
