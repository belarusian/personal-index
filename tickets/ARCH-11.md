Status: CLAIMED 2026-09-07
Kind: ARCH
Author: architect (cycle 174)
Issue: #1016

# ARCH-11: `cli._index_file` is dead code

## Component
`personal_index.cli._index_file` (cli.py, line 1398).

## Symptom
`_index_file(fp, data_dir)` is defined but **never called** anywhere in the
module or the repo (verified: the only call sites for file indexing are
`_index_file_once`, called by `_watch_once` at line 1456). The live path is
`_index_file_once` (line 1419). The two differ only in guard-path style:
`_index_file` indexes when `len(content.strip()) >= 10` (line 1405), while
`_index_file_once` returns early when `len(content.strip()) < 10` (line 1424).
A reader would reasonably assume `_index_file` is the file-indexing helper,
but it is dead.

## Public contract (the code is the truth)
- The live file-indexing helper is `_index_file_once(fp, data_dir) -> None`:
  reads the file (`errors="replace"`), returns without indexing when
  `len(content.strip()) < 10`, else builds a `CrawledPage` and
  `idx.add_page(page)`.
- `_index_file` is not referenced by any code path.

## Acceptance criteria
- `_index_file` is removed (it is dead), OR — if the operator prefers to keep
  it — it is wired into a live path so there is one file-indexing helper, not
  two. Either way, `docs/cli.md` "Private helpers" is updated to match the
  chosen resolution (remove `_index_file` from the list, or reword it to state
  which of the two is live).
- After the change there is exactly ONE file-indexing helper used by
  `_watch_once`.

## Pinning tests to add
`test_watch_once_uses_index_file_once` — run `watch --once` (via the click
`CliRunner`) on a temp dir containing one valid file (>= 10 chars) and one
short file (< 10 chars); assert the valid file is indexed (appears in the
search index) and the short file is not. This pins the live
`_index_file_once` guard path (skip-short-file) and the main path (index
valid file) in one test, so a regression that re-introduces a dead/alternate
indexing helper is caught.

## Docs page it updates
`docs/cli.md` (the `_index_file` helper entry + the contract-holes line, which
this ticket resolves).
