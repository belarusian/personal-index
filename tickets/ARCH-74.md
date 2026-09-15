# ARCH-74 — serializer: `to_csv(include_header=False)` → `from_csv` round-trip silently corrupts the data (first data row consumed as header)

Status: VERIFIED (cycle 228; deep tests tests/deep/test_serializer_adversarial.py arch74_* green; fix correct)
Component: `personal_index/serializer.py` — `Serializer.from_csv` (lines 78-84); the `include_header` parameter of `Serializer.to_csv` (line 67); the `from_csv` docstring (line 79)
Umbrella: ARCH-2 (#983)
Issue: #1411
Docs: `docs/serializer.md` (Contract Hole 1)

## Problem
`to_csv(data, include_header=True)` exposes `include_header` so a caller can
emit a **headerless** CSV. But `from_csv(csv_str)` has no matching parameter:
it always uses `csv.DictReader` with the **first line as the header**. So a
headerless CSV produced by `to_csv(data, include_header=False)` is mis-read on
the way back — the first data row is consumed as the header and the remaining
rows are mapped onto it.

Verified (cycle 242):

    data = [{'name':'Alice','age':'30'},{'name':'Bob','age':'25'}]
    s.to_csv(data, include_header=False)
      -> 'Alice,30\r\nBob,25\r\n'
    s.from_csv(that)
      -> [{'Alice': 'Bob', '30': '25'}]      # column names lost, values mis-mapped

The real column names (`name`, `age`) are gone and the values are re-keyed by
the first row's values — a **silent data-corruption** on a first-class public
path (no exception, no warning). The `include_header=False` parameter exists
precisely to omit the header, but the round-trip partner cannot honor that
omission: there is no way to tell `from_csv` "the first line is data, not a
header." This is the same "advertised capability not actually round-trippable"
class as ARCH-72 (a public path silently does the destructive thing the
docstring omits).

## Public contract (recommended)
`from_csv(csv_str: str, include_header: bool = True,
fieldnames: list[str] | None = None) -> list[dict]`:
- `include_header=True` (default): **unchanged** — first line is the header;
  `fieldnames` is ignored (backward compatible with all existing callers).
- `include_header=False`: `fieldnames` is **required**. If `fieldnames is
  None`, raise `DeserializationError` (column names cannot be inferred from
  headerless data). Otherwise use
  `csv.DictReader(io.StringIO(csv_str), fieldnames=fieldnames)`.
- Empty/whitespace input still returns `[]` (existing guard preserved).

The `from_csv` docstring must state this exact conditional (the first line is
the header unless `include_header=False`, in which case `fieldnames` is
required) rather than the current blanket "Deserialize CSV string to list of
dicts."

## Acceptance criteria
1. `from_csv(s.to_csv(data, include_header=True))` returns `data` (values
   stringified) — backward compatible, unchanged.
2. `from_csv(s.to_csv(data, include_header=False), include_header=False,
   fieldnames=list(data[0].keys()))` returns the same rows as the headered
   round-trip — the headerless round-trip no longer corrupts.
3. `from_csv(headerless_csv, include_header=False)` with `fieldnames=None`
   raises `DeserializationError` (no silent mis-split).
4. `from_csv("")` and `from_csv("   ")` still return `[]` (guard preserved).
5. `from_csv(headered_csv)` with no new args is byte-for-byte the old behavior
   (no caller breakage).

## Pinning tests to add (tests/test_serializer.py)
- **Round-trip-corruption pin (the hole):** build
  `data = [{'name':'Alice','age':'30'},{'name':'Bob','age':'25'}]`; assert
  `from_csv(to_csv(data, include_header=False), include_header=False,
  fieldnames=['name','age']) == [{'name':'Alice','age':'30'},
  {'name':'Bob','age':'25'}]` — pins the corrected round-trip against the
  returned object (not the docstring).
- **Guard-path pin:** assert `from_csv('Alice,30\r\nBob,25\r\n',
  include_header=False)` (no fieldnames) raises `DeserializationError` — pins
  the required-fieldnames guard.
- **Backward-compat pin:** assert `from_csv(to_csv(data)) ==
  [{'name':'Alice','age':'30'},{'name':'Bob','age':'25'}]` with no new args —
  pins the default path as unchanged.
- **Empty-guard pin:** assert `from_csv('') == []` and `from_csv('   ') == []`
  — pins the preserved empty-input guard.

## Docs (SAME PR)
`docs/serializer.md` (new, spec) + the `serializer.md` index entry in
docs/README.md ship in the same PR as this ticket.
