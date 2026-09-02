# TICKET-254: `remove` command leaves orphan tag associations in TagStore

Status: RESOLVED (commit cb678b8, gh #337 closed)
Module: personal_index/cli.py
Issue: #337

## Symptom
The `remove` CLI command (cli.py:901) removes a page from the search index
(`idx.remove_page(p.url)`) but never removes that page's tags from the TagStore.
`TagStore.remove_page(url)` exists precisely for this (tags.py:168: "Remove all
tags for a page"). After `personal-index remove <url>`, the page is gone from the
index but its tag associations remain on disk: `tags list` still counts the removed
page under each tag, and `get_pages_for_tag` still returns the dead URL.

## Evidence
- cli.py:901-917 `remove`: calls `idx.remove_page(p.url)` only; no TagStore call.
- tags.py:168 `TagStore.remove_page(url)` — the intended cleanup, unused by `remove`.
- Parity: `clear --tags` (cli.py:926) clears the whole TagStore; the per-page
  `remove` path omits the per-page equivalent.
- No test documents the leak as intended (only `test_remove_help` exists).

## Minimal additive fix
In `remove`, after `idx.remove_page(p.url)` succeeds (inside the `found` branch),
also call `get_tag_store(dd).remove_page(p.url)` so the page's tags are dropped
alongside the index entry. Output unchanged.
