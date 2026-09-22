"""Adversarial deep tests for personal_index.content_dedup INTERNAL helpers
(cycle 372 probe).

The existing files (test_content_dedup_adversarial.py, 45 pins;
test_content_dedup_dedup_all_adversarial.py, 13 pins) pin the PUBLIC surface
(normalize_url, content_hash, url_hash, text_similarity, DedupResult,
DuplicateGroup, dedup_by_hash/url/similarity, dedup_all, CLI). This file pins
the private helpers those public paths route through, which were never pinned:

  * _group_by_hash: empty items -> {}; missing field -> {}; empty/whitespace
    content skipped (content_hash('') == '' is falsy); unicode content grouped;
    duplicate keys collapse into one hash bucket.
  * _build_dup_groups: empty hash_groups -> ([], 0); single-item groups are
    NOT dups (removed 0); multi-item group -> one DuplicateGroup with
    representative=first, duplicates=rest, score 1.0, method exact_hash,
    removed = len-1; mixed single+multi.
  * _find_similarity_group: seed-only (no later similar) -> [seed url];
    later similar item appended + marked visited; already-visited j skipped;
    out-of-range threshold behaves as plain float comparison.
  * _check_single_item: first item unique; second same-content item dup;
    state accumulates across calls; empty content items DO group (content_hash
    '' -> '' key) unlike dedup_by_hash which skips empty.
  * _dup_result: exact DedupResult shape (total 1, unique 0, removed 1,
    is_duplicate True, one group rep=seen url, dups=[url]).
  * _unique_result: exact DedupResult shape (total 1, unique 1, removed 0,
    is_duplicate False, no groups).

All claims held at HEAD -> regression armor. No slicing idiom in the module
besides the constant content_hash(content)[:16] (no user input, no negative-N
leak).
"""

from __future__ import annotations


from personal_index.content_dedup import (
    ContentDeduplicator,
    DedupResult,
    DuplicateGroup,
    content_hash,
)


# ---------------------------------------------------------------------------
# _group_by_hash
# ---------------------------------------------------------------------------
class TestGroupByHash:
    def test_empty_items_returns_empty_dict(self):
        d = ContentDeduplicator()
        assert d._group_by_hash([], "content") == {}

    def test_missing_field_treated_as_empty_skipped(self):
        d = ContentDeduplicator()
        # item has no "content" key -> item.get("content","") == "" -> hash ""
        # -> falsy -> skipped, so no group is created.
        assert d._group_by_hash([{"url": "a"}, {"url": "b"}], "content") == {}

    def test_empty_and_whitespace_content_skipped(self):
        d = ContentDeduplicator()
        # whitespace-only content hashes to sha256('') (non-empty) so it IS
        # grouped; truly empty content hashes to '' and is skipped.
        groups = d._group_by_hash(
            [{"url": "a", "content": ""},
             {"url": "b", "content": "   "}],
            "content")
        # empty content skipped; whitespace-only content present (1 group).
        assert len(groups) == 1
        urls = [it["url"] for h in groups for it in groups[h]]
        assert "a" not in urls and "b" in urls

    def test_unicode_content_grouped(self):
        d = ContentDeduplicator()
        groups = d._group_by_hash(
            [{"url": "a", "content": "héllo wörld"},
             {"url": "b", "content": "héllo wörld"}],
            "content")
        assert len(groups) == 1
        h = content_hash("héllo wörld")
        assert h in groups and len(groups[h]) == 2

    def test_duplicate_keys_collapse_into_one_bucket(self):
        d = ContentDeduplicator()
        groups = d._group_by_hash(
            [{"url": "a", "content": "same"},
             {"url": "b", "content": "same"},
             {"url": "c", "content": "same"}],
            "content")
        assert len(groups) == 1
        h = content_hash("same")
        assert [it["url"] for it in groups[h]] == ["a", "b", "c"]

    def test_distinct_content_distinct_buckets(self):
        d = ContentDeduplicator()
        groups = d._group_by_hash(
            [{"url": "a", "content": "one"},
             {"url": "b", "content": "two"}],
            "content")
        assert len(groups) == 2


# ---------------------------------------------------------------------------
# _build_dup_groups
# ---------------------------------------------------------------------------
class TestBuildDupGroups:
    def test_empty_hash_groups(self):
        groups, removed = ContentDeduplicator._build_dup_groups({})
        assert groups == [] and removed == 0

    def test_single_item_groups_are_not_dups(self):
        # A hash bucket with exactly one item is not a duplicate group.
        groups, removed = ContentDeduplicator._build_dup_groups(
            {"h1": [{"url": "a"}]})
        assert groups == [] and removed == 0

    def test_multi_item_group_shape(self):
        groups, removed = ContentDeduplicator._build_dup_groups(
            {"h1": [{"url": "a"}, {"url": "b"}, {"url": "c"}]})
        assert removed == 2
        assert len(groups) == 1
        g = groups[0]
        assert isinstance(g, DuplicateGroup)
        assert g.representative == "a"
        assert g.duplicates == ["b", "c"]
        assert g.similarity_score == 1.0
        assert g.dedup_method == "exact_hash"
        assert g.total_count == 3

    def test_mixed_single_and_multi(self):
        groups, removed = ContentDeduplicator._build_dup_groups(
            {"h1": [{"url": "a"}],
             "h2": [{"url": "b"}, {"url": "c"}]})
        assert removed == 1
        assert len(groups) == 1
        assert groups[0].representative == "b"
        assert groups[0].duplicates == ["c"]

    def test_missing_url_key_defaults_empty(self):
        groups, removed = ContentDeduplicator._build_dup_groups(
            {"h1": [{}, {}]})
        assert removed == 1
        assert groups[0].representative == ""
        assert groups[0].duplicates == [""]


# ---------------------------------------------------------------------------
# _find_similarity_group
# ---------------------------------------------------------------------------
class TestFindSimilarityGroup:
    def test_seed_only_no_later_similar(self):
        d = ContentDeduplicator(similarity_threshold=0.9)
        items = [{"url": "a", "content": "alpha beta"},
                 {"url": "b", "content": "gamma delta"}]
        urls = d._find_similarity_group(items, 0, "content", set())
        assert urls == ["a"]

    def test_later_similar_appended_and_visited(self):
        d = ContentDeduplicator(similarity_threshold=0.9)
        items = [{"url": "a", "content": "alpha beta"},
                 {"url": "b", "content": "alpha beta"}]
        visited = set()
        urls = d._find_similarity_group(items, 0, "content", visited)
        assert urls == ["a", "b"]
        assert visited == {0, 1}

    def test_already_visited_j_skipped(self):
        d = ContentDeduplicator(similarity_threshold=0.9)
        items = [{"url": "a", "content": "alpha beta"},
                 {"url": "b", "content": "alpha beta"}]
        # j=1 pre-marked visited -> skipped even though similar.
        urls = d._find_similarity_group(items, 0, "content", {1})
        assert urls == ["a"]

    def test_out_of_range_threshold_no_crash(self):
        # threshold > 1.0 -> no pair reaches it -> seed only.
        d = ContentDeduplicator(similarity_threshold=2.0)
        items = [{"url": "a", "content": "alpha beta"},
                 {"url": "b", "content": "alpha beta"}]
        assert d._find_similarity_group(items, 0, "content", set()) == ["a"]
        # threshold <= 0 -> every non-empty pair qualifies.
        d0 = ContentDeduplicator(similarity_threshold=0.0)
        assert d0._find_similarity_group(items, 0, "content", set()) == ["a", "b"]

    def test_missing_content_field_treated_empty(self):
        d = ContentDeduplicator(similarity_threshold=0.9)
        items = [{"url": "a"}, {"url": "b"}]
        # both empty -> text_similarity 0.0 < 0.9 -> seed only.
        assert d._find_similarity_group(items, 0, "content", set()) == ["a"]


# ---------------------------------------------------------------------------
# _check_single_item
# ---------------------------------------------------------------------------
class TestCheckSingleItem:
    def test_first_item_unique(self):
        d = ContentDeduplicator()
        r = d._check_single_item("a", "t", "hello world")
        assert r.is_duplicate is False
        assert r.unique_items == 1 and r.total_items == 1
        assert r.removed_count == 0 and r.duplicate_groups == []

    def test_second_same_content_is_dup(self):
        d = ContentDeduplicator()
        d._check_single_item("a", "t", "hello world")
        r = d._check_single_item("b", "t", "hello world")
        assert r.is_duplicate is True
        assert r.removed_count == 1
        assert len(r.duplicate_groups) == 1
        g = r.duplicate_groups[0]
        assert g.representative == "a"
        assert g.duplicates == ["b"]

    def test_state_accumulates_across_calls(self):
        d = ContentDeduplicator()
        d._check_single_item("a", "t", "one")
        d._check_single_item("b", "t", "two")
        # third item repeats "one" -> dup of "a".
        r = d._check_single_item("c", "t", "one")
        assert r.is_duplicate is True
        assert r.duplicate_groups[0].representative == "a"
        assert r.duplicate_groups[0].duplicates == ["c"]

    def test_empty_content_items_do_group(self):
        # Unlike dedup_by_hash (which skips empty content), _check_single_item
        # keys on content_hash('') == '' so two empty items DO collide.
        d = ContentDeduplicator()
        r1 = d._check_single_item("a", "t", "")
        r2 = d._check_single_item("b", "t", "")
        assert r1.is_duplicate is False
        assert r2.is_duplicate is True
        assert r2.duplicate_groups[0].representative == "a"

    def test_whitespace_normalized_collision(self):
        d = ContentDeduplicator()
        d._check_single_item("a", "t", "hello   world")
        r = d._check_single_item("b", "t", "hello world")
        assert r.is_duplicate is True


# ---------------------------------------------------------------------------
# _dup_result / _unique_result
# ---------------------------------------------------------------------------
class TestResultBuilders:
    def test_dup_result_exact_shape(self):
        d = ContentDeduplicator()
        d._seen_hashes = {"h": "seen-url"}
        r = d._dup_result("new-url", "h")
        assert isinstance(r, DedupResult)
        assert r.total_items == 1 and r.unique_items == 0
        assert r.removed_count == 1 and r.is_duplicate is True
        assert r.method == "hash"
        assert len(r.duplicate_groups) == 1
        g = r.duplicate_groups[0]
        assert g.representative == "seen-url"
        assert g.duplicates == ["new-url"]
        assert g.similarity_score == 1.0
        assert g.dedup_method == "exact_hash"

    def test_unique_result_exact_shape(self):
        r = ContentDeduplicator._unique_result()
        assert isinstance(r, DedupResult)
        assert r.total_items == 1 and r.unique_items == 1
        assert r.removed_count == 0 and r.is_duplicate is False
        assert r.method == "hash"
        assert r.duplicate_groups == []
