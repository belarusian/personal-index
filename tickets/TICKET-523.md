# TICKET-523: Reword ContentAPI._list_content docstring to exact contract + pinning test

**Status:** RESOLVED
**Issue:** #912 (merged via PR #913; supersedes stale #908/#914)

## Title
Reword personal_index/content_api.py ContentAPI._list_content docstring to state its exact dispatch contract, and add a pinning test that asserts the docstring contains the key contract phrases.

## Symptom
The _list_content method currently has no docstring. The method implements pagination with specific defaults, validation, and response shape, but no docstring documents the exact contract.

## Evidence
File: personal_index/content_api.py
Line: ~124
Behavior (verified in tests/test_content_api.py TestListContent):
- params dict with optional page (default 1) and per_page (default 20)
- returns (400, {error}) when page or per_page is not an integer
- per_page is capped at 100
- returns (200, {items, total, page, per_page}) on success

## Minimal Additive Fix
1. Add a docstring to _list_content stating the exact contract: params read (page default 1, per_page default 20), the 400 error on non-integer page/per_page, the per_page cap of 100, and the 200 response shape {items, total, page, per_page}.
2. Add a pinning test in tests/test_content_api.py asserting the docstring contains the key contract phrases.

## Status
RESOLVED

## Resolution
Docstring added to ContentAPI._list_content and pinning test merged on main via PR #913 (issue #912). Duplicate PR #915 / issue #914 (this cycle) and stale PR #909 / issue #908 closed as superseded.
