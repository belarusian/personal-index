# Contract Docstring Standard

This is the de-facto standard established across cycles 155-168 (the
"exact-contract docstring" work) and is now the ARCHITECT's binding contract
for every public function in `personal_index/**`.

A **contract docstring** states, in the function's own docstring, exactly what
the function does — no blanket adjectives, no over-promises. It has three
required parts:

1. **Guard paths.** Every early-return / skip / falsy-input branch, stated as
   the exact value returned on that path (e.g. "no recorded events -> returns
   exactly `{"total": 0}` (no other keys)"). If there is no guard path, say so
   explicitly ("no guard path: always computes").
2. **Return-object fields.** The exact fields of the returned object, each with
   its computation (e.g. "returns a dict with 8 fields — total, avg_results,
   max_results, min_results, avg_duration_ms, max_duration_ms,
   click_through_rate, unique_queries — where durations are counted only when
   `duration_ms > 0` and `click_through_rate = clicked / total`"). Never a
   blanket adjective like "computed" / "normalizes case" / "without breaking
   words" / "recommended".
3. **Side effects.** Any mutation, persistence, or I/O the function performs
   (e.g. "persists to `db_path` via `_save()`"), or "no side effects" if none.

## Pinning tests

Every contract docstring is witnessed by **ONE behavior test** that asserts the
**RETURNED OBJECT** (not counters, not substrings, not the docstring wording).
The test must cover:

- the **normal case** (all return fields with exact values), and
- the **guard-path input** the docstring now states (the skip / early-return /
  falsy-input case — e.g. an empty-content item, an unsupported format, a
  falsy url), so one returned object pins both the main behavior and the guard
  path.

This makes the fix witnessed as doc-only: if the code later drifts from the
docstring, the pinning test fails.

## Line-shift guard

A docstring reword that ADDS lines shifts every subsequent line number in the
file. Before committing, grep the WHOLE `tests/` tree (every test file, not
just the one for the module being edited) for line-number references
(`lineno` / `getsource` / `_get_source_lines` / `_method_line_span`). A LITERAL
line-number pin (hardcoded `lineno` / `_get_source_lines` range) is the real
risk; `inspect.getsource(func)` and `_method_line_span(name)` resolve by
function object / name via AST, so added docstring lines are SAFE for those.

## How to apply

For each target function:
1. Read the function body; enumerate guard paths, return fields, side effects.
2. Reword the docstring to state exactly those (parts 1-3 above).
3. Add ONE pinning test asserting the returned object for normal + guard input.
4. Run the line-shift grep over `tests/`.
5. Run the local gate (pytest + ruff + mypy).
