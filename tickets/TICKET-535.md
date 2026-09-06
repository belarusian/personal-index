# TICKET-535: ContentDiff.compute docstring omits exact contract

Status: OPEN
Module: personal_index/content_diff/changes.py
Method: ContentDiff.compute (classmethod, def at line ~70)

## Symptom
The `compute` docstring is a single terse line:
    "Compute the diff between two content items."
It does NOT state the exact contract that the code actually delivers:
  - item_id resolution fallback chain: str(new_item.get(id_field,
    old_item.get(id_field, "unknown"))) -- new item first, then old item,
    then the literal string "unknown";
  - the field set diffed is the SORTED UNION of old_item and new_item keys
    (set(old) | set(new), iterated in sorted order);
  - each field is classified ADDED (only in new), REMOVED (only in old),
    or MODIFIED (in both but values differ); unchanged fields are dropped;
  - summary is built by _summary_text as "N added, N removed, N modified"
    (that fixed order, zero-count types omitted) or "No changes" when there
    are no changes.
A reader of the docstring cannot tell any of this. Sibling methods in the
same module (get_changes_by_type) already carry exact-contract docstrings;
compute is the remaining un-documented public entry point.

## Evidence (verified by running the code)
  compute({'id':'1'},{'id':'2'}).item_id            -> '2'   (new wins)
  compute({'id':'1'},{}).item_id                    -> '1'   (old fallback)
  compute({},{}).item_id                            -> 'unknown'
  compute({'uid':'x1'},{'uid':'x2'},id_field='uid') -> 'x2'
  compute({'id':'1','a':'x','b':'y','c':'z'},
          {'id':'1','b':'Y','d':'w'})
    changes -> [('a','removed'),('b','modified'),('c','removed'),('d','added')]
    summary -> '1 added, 2 removed, 1 modified'
  compute({'id':'1'},{'id':'1'}).summary            -> 'No changes'

Existing behavioral tests already pin most of this (tests/test_content_diff.py
TestContentDiff: test_no_changes, test_added_field, test_removed_field,
test_modified_field, test_summary_text, test_id_field_custom,
test_id_unknown). The behavior is correct; only the docstring contract is
missing.

## Minimal additive fix
Reword the compute docstring to state the exact contract (item_id fallback
chain, sorted-union field set, ADDED/REMOVED/MODIFIED classification, summary
format/order and the "No changes" case). Add a pinning test class
TestComputeDocstring535 mirroring the TestClearDocstring533 /
TestCreateSnapshotDocstring534 pattern, asserting the docstring states the
contract (key phrases: "item_id", "union"/"sorted", "added", "removed",
"modified", "No changes").

## Issue
Issue: #946
