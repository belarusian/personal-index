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

## Negative-slice guard (binding)

Any public function whose contract is "return the top N / first N / most
recent N items" — i.e. any function that truncates a list with `list[:N]`
(plain form) or `list[offset:offset+N]` (offset form) where `N` is a
caller-supplied count / limit / top_n / n / count — MUST guard `N <= 0 -> []`
(return an empty list). A non-positive `N` is out-of-range and must yield the
same empty result as the zero bound; a negative `N` must NOT leak Python
negative-slice semantics (`list[:-1]` = all-but-last, and in the offset form
`list[offset:offset-1]` = a shifted window). The guard short-circuits BEFORE
the slice. The guard is stated in the function's contract docstring (part 1,
guard paths) and witnessed by ONE pinning test that asserts the returned
object for both `N < 0` and `N == 0` (both `== []`). This rule is the single
home for the negative-slice-truncation class (ARCH-17); per-site instances
(ARCH-15, QA-1, QA-2, QA-3, QA-15 #1186, QA-16 #1191) reference it.

## Defensive-load guard (binding)

Any private `_load` method whose contract is "rebuild in-memory state from a
persisted JSON mapping" — i.e. any method that `json.load`s a file, checks
`isinstance(data, dict)`, and iterates `data.items()` constructing a per-key
object from each value — MUST degrade to the empty state on ANY malformed
value: a value that is not a mapping, or a mapping whose fields have the wrong
type. A malformed value is out-of-range and must yield the same empty state as
a missing file; construction MUST NOT raise. The guard is stated in the
method's contract docstring (part 1, guard paths) and witnessed by ONE
pinning test that asserts the constructed state for a non-dict value (== empty
state) ALONGSIDE the normal case. This rule is the single home for the
defensive-load-crash class (ARCH-63); per-site instances (QA-11, QA-17)
reference it.

## Divisor guard (binding)

Any public helper whose contract is "compute a count/rate/minutes value by
dividing by a caller-supplied scalar" — i.e. any function that performs
`count / divisor` (or `count // divisor`) where `divisor` is a caller-supplied
scalar such as `wpm`, `per_page`, `window_seconds`, `rate`, `n` — MUST guard
the divisor: **`divisor <= 0` -> return a defined safe result (no division,
no exception, no silent wrong value)**; `divisor > 0` -> the normal
computation. A non-positive divisor is out-of-range and must short-circuit to
the safe result BEFORE the division; it must NOT raise `ZeroDivisionError`
and must NOT silently return a clamped/wrong value (e.g. a bogus `1`). The
guard is stated in the function's contract docstring (part 1, guard paths)
and witnessed by ONE pinning test that asserts the returned value for the
guard inputs (`divisor == 0` and `divisor < 0`) ALONGSIDE the normal positive
case. This rule is the single home for the guard-the-raw-divisor class
(ARCH-64); per-site instances reference it (ARCH-58 pagination `per_page`,
ARCH-59 throttle `window_seconds`, ARCH-60 `read_time_minutes` `wpm`).

## How to apply

For each target function:
1. Read the function body; enumerate guard paths, return fields, side effects.
2. Reword the docstring to state exactly those (parts 1-3 above).
3. Add ONE pinning test asserting the returned object for normal + guard input.
4. Run the line-shift grep over `tests/`.
5. Run the local gate (pytest + ruff + mypy).
6. If the function truncates with `list[:N]` or `list[offset:offset+N]` on a
   caller-supplied count, apply the **Negative-slice guard** rule above
   (`N <= 0 -> []`, short-circuit before the slice).
7. If the method is a `_load` that rebuilds state from a persisted JSON
   mapping, apply the **Defensive-load guard** rule above (degrade to the
   empty state on any malformed value; construction must not raise).
8. If the function divides by a caller-supplied scalar
   (`count / divisor`), apply the **Divisor guard** rule above (`divisor <= 0`
   -> defined safe result, no division, no exception, no silent wrong value).
