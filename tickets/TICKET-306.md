# TICKET-306: storage.py Storage._read_json unguarded json.loads crashes on corrupt file

- Status: OPEN
- Module: personal_index/storage.py
- Class: (c) unguarded json.loads + missing corrupt-file guard (violates the module's own default-degradation contract)
- Site: personal_index/storage.py:29-35 - `def _read_json(self, filepath: Path) -> list | dict:`

## Symptom
`_read_json` establishes a clean degradation contract for an empty file: it returns
`[]` for `interests.json`/`pages.json` and `{}` otherwise (lines 31-34). But the
parse step (line 35) calls `json.loads(content)` with no guard. A malformed
`interests.json` / `config.json` / `pages.json` (truncated write, hand-edit, disk
corruption) raises a raw `json.JSONDecodeError` straight out of every public
accessor (`add_interest`, `get_interests`, `load_config`, `get_pages`, ...),
instead of degrading to the same default the empty-file branch already returns.

## Evidence (verified against the body)
- Line 35: `return json.loads(content)  # type: ignore[no-any-return]` — no try/except.
- Lines 31-34 already define the per-file default (`[]` for interests/pages, `{}`
  otherwise) that a corrupt file should fall back to, exactly as an empty file does.
- storage.py is NOT in the closed corrupt-JSON-guard class (that list is
  bookmarks / content_search / analytics / session / backup / cycle_signals).

## Minimal additive fix
Wrap the parse in `except json.JSONDecodeError` and return the same default already
used for an empty file (factor the default into a small helper so the empty and
corrupt branches share one source of truth).

## Regression test
Add tests writing malformed JSON to each of interests.json / config.json / pages.json
and asserting the accessors degrade to the documented default ([]/{}/[]) rather than
raising.

## Issue: #445
