"""content_dedup.dedup_all adversarial deep tests (validator cycle 355).

Probes the dedup_all three-stage pipeline (url -> hash -> similarity rebuild)
for empty-key collapse, invariants, idempotence, and the CLI end-to-end path.

QA-74: the URL/hash rebuild stages collapse all-but-first items that share an
empty normalize_url / content_hash key, but the dropped item is never counted
in removed_count, so unique_items overstates the true survivor count (silent
data loss). The defect pin below is xfail-strict and linked to QA-74.
"""

from __future__ import annotations

import os
import subprocess
import sys

from personal_index.content_dedup import (
    ContentDeduplicator,
    content_hash,
    normalize_url,
    text_similarity,
)


def _survivors(items):
    """Replay the documented dedup_all rebuild stages (url then hash) and
    return the items that actually survive the pipeline."""
    seen = set()
    uniq = []
    for it in items:
        n = normalize_url(it.get("url", ""))
        if n not in seen:
            seen.add(n)
            uniq.append(it)
    seen2 = set()
    huniq = []
    for it in uniq:
        h = content_hash(it.get("content", ""))
        if h not in seen2:
            seen2.add(h)
            huniq.append(it)
    return huniq


class TestDedupAllInvariants:
    def test_empty_input(self):
        r = ContentDeduplicator().dedup_all([])
        assert r.total_items == 0
        assert r.unique_items == 0
        assert r.removed_count == 0
        assert r.duplicate_groups == []
        assert r.dedup_ratio == 0.0
        assert r.method == "combined"

    def test_all_distinct_no_groups(self):
        items = [
            {"url": "a.com", "content": "one"},
            {"url": "b.com", "content": "two"},
            {"url": "c.com", "content": "three"},
        ]
        r = ContentDeduplicator().dedup_all(items)
        assert r.total_items == 3
        assert r.removed_count == 0
        assert r.unique_items == 3
        assert r.duplicate_groups == []

    def test_exact_url_dup_counted(self):
        items = [
            {"url": "a.com", "content": "x"},
            {"url": "a.com", "content": "y"},
        ]
        r = ContentDeduplicator().dedup_all(items)
        assert r.removed_count == 1
        assert r.unique_items == 1
        assert len(r.duplicate_groups) == 1

    def test_unique_items_equals_total_minus_removed(self):
        items = [
            {"url": "a.com", "content": "x"},
            {"url": "a.com", "content": "y"},
            {"url": "b.com", "content": "z"},
        ]
        r = ContentDeduplicator().dedup_all(items)
        assert r.unique_items == r.total_items - r.removed_count

    def test_idempotent_on_distinct(self):
        items = [
            {"url": "a.com", "content": "one"},
            {"url": "b.com", "content": "two"},
        ]
        d = ContentDeduplicator()
        r1 = d.dedup_all(items)
        r2 = d.dedup_all(items)
        assert r1.total_items == r2.total_items
        assert r1.removed_count == r2.removed_count
        assert r1.unique_items == r2.unique_items

    def test_missing_keys_do_not_crash(self):
        items = [{"url": "a.com"}, {"content": "x"}, {}]
        r = ContentDeduplicator().dedup_all(items)
        assert r.total_items == 3
        assert r.unique_items == r.total_items - r.removed_count

    def test_unicode_url_and_content(self):
        items = [
            {"url": "café.com/☕", "content": "héllo wörld"},
            {"url": "café.com/☕", "content": "héllo wörld"},
        ]
        r = ContentDeduplicator().dedup_all(items)
        assert r.removed_count == 1
        assert r.unique_items == 1


class TestDedupAllEmptyKeyDataLoss:
    def test_empty_url_distinct_content_survivor_count_matches_unique_items(self):
        # QA-74 (fixed): the URL rebuild loop's empty-key drop is now counted
        # in removed_count, so unique_items reflects the true survivor count.
        # Two genuinely distinct items (different content) both with an empty
        # URL. The URL rebuild loop retains only the first empty-URL item and
        # now counts the drop, so unique_items == 1 == the true survivor count.
        items = [
            {"url": "", "content": "alpha"},
            {"url": "", "content": "beta"},
        ]
        r = ContentDeduplicator().dedup_all(items)
        survivors = _survivors(items)
        # Invariant: the reported unique_items must equal the number of items
        # that actually survive the documented rebuild stages.
        assert len(survivors) == r.unique_items, (
            f"survivors={len(survivors)} unique_items={r.unique_items} "
            f"removed_count={r.removed_count}"
        )

    def test_empty_content_distinct_url_survivor_count_matches_unique_items(self):
        # QA-74 (fixed): the hash rebuild loop's empty-key drop is now counted
        # in removed_count, so unique_items reflects the true survivor count.
        # Two distinct items (different URL) both with empty content. The hash
        # rebuild stage collapses them to one survivor and now counts the drop.
        items = [
            {"url": "a.com", "content": ""},
            {"url": "b.com", "content": ""},
        ]
        r = ContentDeduplicator().dedup_all(items)
        survivors = _survivors(items)
        assert len(survivors) == r.unique_items, (
            f"survivors={len(survivors)} unique_items={r.unique_items} "
            f"removed_count={r.removed_count}"
        )


class TestTextSimilarityEdge:
    def test_punctuation_only_zero(self):
        assert text_similarity("!!! ???", "###") == 0.0

    def test_unicode_tokens_zero(self):
        # [a-z0-9]+ tokens: pure-unicode input yields empty word sets -> 0.0
        assert text_similarity("☕☕", "☕☕") == 0.0
        assert text_similarity("éé", "éé") == 0.0

    def test_mixed_case_folded(self):
        assert text_similarity("Hello World", "hello world") == 1.0


class TestCliEndToEnd:
    def test_cli_dedup_all_runs_cleanly(self, tmp_path):
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)
        env = dict(os.environ)
        r = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "dedup", "--method", "all"],
            capture_output=True, text=True, env=env,
        )
        assert r.returncode == 0, r.stderr
        # Empty index: the command runs cleanly and reports no content.
        assert "No indexed content found." in r.stdout
