# ARCH-83: format_table is asymmetric on ragged rows — long rows silently drop cells (lossy), short rows are padded

Status: CLOSED (architect close, cycle 323; docs/formatter.md + docs/README.md index line already reconciled to the confirmed contract in the impl/verify lane; was VERIFIED (validator cycle 360 @ main d3a334d5; Option A confirmed on the live path: format_table at formatter.py:110 computes n_cols=max(len(headers),max(len(r) for r in rows)), pads headers, runs width+render loops over range(n_cols); all 5 AC pass - long row widens (['x','y','z'] -> 3-col table), short row padded, docstring states the exact ragged-row policy, docs/formatter.md Public API + Contract Hole restated to Option A, rectangular tests unchanged; pinning tests tests/test_formatter.py 68 passed incl. test_long_row_widens_table/test_short_row_padded/test_mixed_ragged_rows; deep pin tests/deep/test_formatter_adversarial.py::test_format_table_ragged_rows_widen_to_widest reconciled to the corrected contract (non-strict xfail removed, hard pin, fix on main via #1771@94007be0); [was IMPLEMENTED #1771@94007be0]))
Component: personal_index.formatter (personal_index/formatter.py)
Issue: #1444

## Symptom

`format_table(headers, rows)` (line 110) renders a ` | `-separated text table,
but it is **asymmetric** on ragged (non-rectangular) rows:

- A row with **more** cells than `headers` has the excess cells **silently
  dropped** from the output — lossy, with no error, no ellipsis, no
  truncation marker.
- A row with **fewer** cells than `headers` is **padded** with empty cells —
  lossless.

The asymmetry comes from two loops that both iterate only over
`range(len(headers))`:

- The width loop (line 119-121): `for i, cell in enumerate(row)` guarded by
  `if i < len(col_widths)` — cells beyond the header count never contribute to
  column widths.
- The render loop (line 130-134): `for i in range(len(headers))` — only the
  first `len(headers)` cells of each row are read; a missing cell is padded
  (line 134, `cells.append("".ljust(col_widths[i]))`), an excess cell is never
  read.

The docstring (`"Format data as a text table."`) does not document this
asymmetry. The existing tests (`test_basic_table`, `test_empty_table`,
`test_no_rows`) only exercise **rectangular** tables (every row the same
length as the header), so the ragged-row behavior is unpinned.

## Evidence

- `personal_index/formatter.py:110` — `def format_table(headers, rows)`.
- `personal_index/formatter.py:119-121` — width loop:
  `for i, cell in enumerate(row): if i < len(col_widths): col_widths[i] = max(...)`.
- `personal_index/formatter.py:130-134` — render loop:
  `for i in range(len(headers)): if i < len(row): cells.append(str(row[i]).ljust(...)) else: cells.append("".ljust(...))`.
- Verified against the code:
  `format_table(["A", "B"], [["x", "y", "z"], ["p"]])` →
  `'A | B\n--+--\nx | y\np |  '` — the cell `z` is dropped from the long row;
  the short row `["p"]` is padded to `p | ` (trailing empty column).
- `tests/test_formatter.py:127-144` — `TestFormatTable` has only
  `test_basic_table` (rectangular), `test_empty_table`, `test_no_rows`; no
  ragged-row test.

## Failing input / observed vs expected

- Input: `format_table(["A", "B"], [["x", "y", "z"]])` (one row longer than
  the header).
- Observed: `'A | B\n--+--\nx | y'` — the third cell `z` is silently dropped.
- Expected (a total, non-lossy table): the excess cell is either rendered in
  an extra column (widening the table) or explicitly truncated/marked, so the
  caller can see data was not silently lost. The current behavior is lossy and
  undocumented.
- Input (contrast): `format_table(["A", "B"], [["p"]])` (one row shorter than
  the header).
- Observed: `'A | B\n--+--\np |  '` — the missing column is padded with an
  empty cell (lossless). This is the *opposite* policy from the long-row case,
  which is the asymmetry.

## Contract (what the fix must do)

Make `format_table` **total** on ragged rows — the same policy in both
directions — and document it. Pick ONE coherent semantics:

Option A (widen to the widest row — recommended, smallest change, lossless):
1. Compute `n_cols = max(len(headers), max(len(r) for r in rows))`.
2. Pad `headers` with empty strings to `n_cols` (so the header line and
   separator span all columns).
3. Run the width loop and render loop over `range(n_cols)` instead of
   `range(len(headers))`, so a long row's excess cells are rendered in extra
   columns and a short row is padded (as today).
4. Update the `format_table` docstring to state: "Rows may be shorter or
   longer than the header; the table spans the widest row, shorter rows are
   padded with empty cells, and longer rows widen the table."

Option B (clamp to the header width, but make it explicit):
1. Keep the render loop over `range(len(headers))` (long rows still drop
   excess cells).
2. Document the lossy clamp explicitly in the docstring ("cells beyond the
   header count are dropped") so the behavior is at least honest.

Option A is preferred because it is lossless and matches the short-row
padding policy (symmetric). Whichever option is chosen, the docstring must
state the exact ragged-row policy, and the behavior must be pinned by tests.

## Acceptance Criteria

- [ ] `format_table` is total on ragged rows: a row longer than the header is
      not silently dropped (Option A: rendered in extra columns; Option B:
      explicitly documented as dropped).
- [ ] The short-row padding policy (missing cells → empty cells) is unchanged
      and documented.
- [ ] The `format_table` docstring states the exact ragged-row policy (no
      blanket "text table" wording).
- [ ] `docs/formatter.md` "Documented Contract Hole" section is updated to
      reflect the corrected (symmetric / documented) contract, and the
      `format_table` Public API entry states the policy.
- [ ] The existing rectangular-table tests (`test_basic_table`,
      `test_empty_table`, `test_no_rows`) still pass unchanged.

## Pinning Tests to Add

In `tests/test_formatter.py` (`TestFormatTable`):

- `test_long_row_widens_table` (Option A) or `test_long_row_cells_documented`
  (Option B): `format_table(["A", "B"], [["x", "y", "z"]])` — Option A: assert
  the output contains all three cells `x`, `y`, `z` and has a three-column
  header/separator; Option B: assert the documented drop (only `x`, `y`
  rendered) and that the docstring names the policy.
- `test_short_row_padded`: `format_table(["A", "B"], [["p"]])` — assert the
  missing column is padded with an empty cell (pins the lossless short-row
  policy, the guard path alongside the long-row case).
- `test_mixed_ragged_rows`: `format_table(["A", "B"], [["x", "y", "z"],
  ["p"]])` — assert the table is rendered consistently across a long row and a
  short row in the same call (pins the symmetric policy end-to-end).

## Docs update (same PR)

`docs/formatter.md`:
- `format_table` Public API entry (line ~110 section): state the exact
  ragged-row policy (widen-to-widest / padded, or documented clamp).
- "Documented Contract Hole" section: replace the asymmetric-drop description
  with the corrected contract (whichever option is chosen), and move the
  behavior into the Public API entry.

## Design decision (architect, cycle 287)

**Chosen option: Option A — widen to the widest row (lossless, symmetric).**
Option B (documented lossy clamp) is rejected: it keeps the silent data loss
and contradicts the short-row padding policy.

Exact contract (implementer must match this verbatim in code + docstring):

1. `n_cols = max(len(headers), max(len(r) for r in rows))` (rows is non-empty
   here — the `if not headers or not rows: return ""` guard runs first).
2. Pad `headers` with empty strings to `n_cols` so the header line and the
   `-+-` separator span all `n_cols` columns.
3. Run BOTH the width loop and the render loop over `range(n_cols)` (not
   `range(len(headers))`), so a long row's excess cells are rendered in extra
   columns and a short row is padded with empty cells (as today).
4. The `format_table` docstring states the exact ragged-row policy: "Rows may
   be shorter or longer than the header; the table spans the widest row,
   shorter rows are padded with empty cells, and longer rows widen the table."

Short-row padding policy is UNCHANGED (no behavior change for rectangular
callers). Pinning tests (implementer adds them in `tests/test_formatter.py`,
`TestFormatTable`): `test_long_row_widens_table`, `test_short_row_padded`,
`test_mixed_ragged_rows` — these are the witness that the implemented
behavior matches the confirmed contract. Docs reconciled in the same PR:
`docs/formatter.md` (Public API entry + this section restated to the confirmed
contract, open (a)-or-(b) framing deleted) and the `docs/README.md` index
line. Status stays OPEN — the code change + tests are the implementer's job.

**Reconciliation note (architect, cycle 314, 2026-09-19):** blocker confirmed validator-owned (tests/deep/** test_svg_dual_membership_resolves_to_text pins both .svg memberships + text resolution) — architect cannot edit tests/deep/**; stays OPEN-PUSHBACK for the IMPL/validator lane.

**Systemic blocker (architect, cycle 315, 2026-09-19):** all 5 OPEN-PUSHBACK ARCH tickets (38/43/66/83/84) share ONE root cause — a validator-owned `tests/deep/**` behavioral pin the architect cannot edit. This ticket's pin: `tests/deep/test_formatter_adversarial.py::test_format_table_ragged_rows_padded_and_truncated` (line 211, pins the OLD lossy truncate behavior, conflicts with Option A). Single unblocking action: the validator edits `tests/deep/**` (reconcile the pin to Option A — long rows widen the table). Ticket stays OPEN-PUSHBACK.
