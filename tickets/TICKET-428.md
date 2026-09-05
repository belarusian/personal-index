# TICKET-428: bookmark_export.export_to_file - implement missing write-failure path so ORIGINAL "result with errors on failure" claim is true

Status: RESOLVED
Issue: #694

## File
personal_index/bookmark_export.py (export_to_file, ~line 166-210)

## Symptom
The docstring (stable since module creation 0abed9d9, never downgraded) claims:
"A BookmarkExportResult on success, or a result with errors on failure."
The write path (`with open(filepath, "w", encoding="utf-8") as f: f.write(content)`
at line 197) has NO try/except. An OSError (permission denied, missing parent
directory, read-only fs) propagates to the caller instead of returning a
BookmarkExportResult with errors. The "result with errors on failure" half of the
claim is only honored for the two pre-write failure branches (unsupported format,
export returned None), not for the actual file-write failure.

## Evidence
- personal_index/bookmark_export.py:197 `with open(filepath, "w", encoding="utf-8") as f:`
  - no surrounding try/except (grep of export_to_file body shows zero try/except).
- Original claim at 0abed9d9 (module creation) is byte-identical to current
  docstring: "A BookmarkExportResult on success, or a result with errors on failure."
- No reword commit exists for this function (git log -p on all commits touching
  bookmark_export.py: only TICKET-323 changed the RETURN ANNOTATION, not the
  docstring; docstring unchanged since 0abed9d9).

## Classification
IMPLEMENTABLE (claim-truth, code-not-docs). The original claim is recoverable and
the missing behavior is a bounded try/except around the write, mirroring the
cycle-55 content_pin.unpin fix.

## Minimal additive fix
Wrap the write in try/except OSError; on failure return
`BookmarkExportResult(errors=[f"Failed to write file: {filepath}: {exc}"])`.
Re-pin the pinning test to the ORIGINAL claim: add a test that monkeypatches
builtins.open to raise OSError and asserts a BookmarkExportResult with non-empty
errors is returned (not raised). Keep existing success/unsupported tests.

## Numbering note
Renumbered from 427 -> 428: the parallel personal-index pipeline claimed
TICKET-427 (content_collections.CollectionManager.add_item, gh #691) and merged it
to main (588af37) during this cycle. Same-number collision on a different file
(cycles 53, 55 pattern). This lineage's ticket renumbered to the next free number.

## Do NOT
- Do not downgrade the docstring (original claim is implementable).
- Do not touch the parallel pipeline's in-flight TICKET-426/427 (collections).
