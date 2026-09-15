# ARCH-76 — url_history: `URLHistory.load` raises `TypeError` on a valid-JSON list whose records are malformed (unexpected key or missing `url`), breaking its graceful-degradation contract

Status: VERIFIED (validator cycle 230; 5 ACs pass; wrong-type url discrepancy scoped out to QA-38 #1455)
Component: `personal_index/url_history.py` — `URLHistory.load` (lines 157-171); the `URLVisit.from_dict` comprehension inside it (line 169); the `load` docstring (line 158)
Umbrella: ARCH-2 (#983)
Issue: #1415
Docs: `docs/url_history.md` (Contract Hole, ARCH-76)

## Problem
`load` promises graceful degradation: its docstring says "Load history from
file. Returns count loaded." and the body returns `0` for three bad inputs —
missing file (line 160-161), invalid JSON (`except json.JSONDecodeError`,
lines 165-167), and a parsed value that is not a list (lines 168-169).

But the reconstruction step

    self._history = [URLVisit.from_dict(d) for d in data]   # line 169

runs **outside** the `try/except json.JSONDecodeError` block. `from_dict`
builds via `cls(**data)` (line 44), so a record that (a) carries a key that is
not a `URLVisit` field name, or (b) omits `url` (which has no default), raises
`TypeError` from the dataclass constructor. That `TypeError` propagates out of
`load` — the caller gets an exception, not the `0` the contract implies.

So `load` is graceful for *structurally* bad files (missing / not-JSON /
non-list) but **not** for a *well-formed JSON list of malformed records*. A
corrupt or hand-edited history file that is still valid JSON (e.g. a record
with a typo'd key, or a record missing `url`) crashes the load instead of
degrading. The existing tests pin only the non-list and corrupt-JSON guards
(`TestURLHistoryNonListGuard`, `TestURLHistoryCorruptJSONGuard` in
`tests/test_url_history.py`) — none pins a valid-list-with-malformed-record.

Verified (cycle 244):

    h = URLHistory()
    p = tmp / "h.json"
    p.write_text('[{"url": "http://a.com", "bogus_key": 1}]')
    h.load(str(p))   # raises TypeError: __init__() got an unexpected keyword argument 'bogus_key'

    p.write_text('[{"status_code": 200}]')   # valid JSON list, missing url
    h.load(str(p))   # raises TypeError: __init__() missing 1 required positional argument: 'url'

This is the same "public path does the thing the docstring omits" class as
ARCH-72 / ARCH-74 / ARCH-75.

## Public contract (recommended)
`load(self, filepath: str) -> int`:
- Returns `0` (and leaves `_history` untouched) for: missing file, invalid
  JSON (`json.JSONDecodeError`), a parsed value that is not a list, **and** a
  list containing one or more records that `URLVisit.from_dict` cannot
  construct (unexpected key, missing `url`, or a value of the wrong type for a
  field).
- When every record is constructible, behavior is **exactly as today**:
  `_history` is replaced, `_trim()` is called, and the loaded count is
  returned.
- The reconstruction must be guarded so a malformed record degrades to the
  same `0`-return path as the other bad inputs (e.g. wrap the comprehension in
  the same `try/except`, or validate each record before constructing). The
  exact mechanism is the implementer's choice; the observable contract is
  "never raises on file contents, returns the number of visits actually
  loaded."
- `save`, `record`, `get_visits`, `get_unique_urls`, `get_stats`,
  `get_domain_stats`, `clear`, `_trim`, and `URLVisit` (all methods) are
  unchanged.

The `load` docstring must state the exact degradation set (missing / invalid
JSON / non-list / malformed record all return `0`) rather than the current
blanket "Load history from file. Returns count loaded."

## Acceptance criteria
1. `load` of a file containing a valid-JSON list with a record that has an
   unexpected key returns `0` and does **not** raise; `_history` is empty.
2. `load` of a file containing a valid-JSON list with a record missing `url`
   returns `0` and does **not** raise; `_history` is empty.
3. `load` of a well-formed list (all records constructible) still returns the
   count and populates `_history` exactly as today (existing
   `test_load_valid_list_still_works` stays green).
4. The existing guards stay green: missing file, `null`/number/dict (non-list),
   and corrupt/truncated JSON all still return `0`.
5. `save` -> `load` round-trip of a populated history is unchanged (existing
   `test_save_and_load` stays green).

## Pinning tests to add (tests/test_url_history.py)
- **Malformed-record pin (the hole):** write a valid-JSON list
  `[{"url": "http://a.com", "bogus_key": 1}]`, assert `load` returns `0` and
  does not raise, and `get_visits()` is empty — pins the corrected behavior
  against the returned count, not the docstring.
- **Missing-url pin (guard path):** write `[{"status_code": 200}]` (valid JSON
  list, no `url`), assert `load` returns `0` and does not raise — pins the
  missing-required-field guard, not just the unexpected-key case.
- **Normal-list pin:** the existing well-formed-list case still returns the
  count and populates `_history` (guards against over-broad degradation that
  would reject valid records).

## Docs (SAME PR)
`docs/url_history.md` (new, spec) + the `url_history.md` index entry in
docs/README.md ship in the same PR as this ticket.
