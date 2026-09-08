Status: IN PROGRESS (cycle 189: content_summarizer in progress; cycle 188: content_timeline done PR #1083@e6cbbc3; cycle 187 cache done PR #1080@fd1eea6; cycle 186 content_dedup done PR #1079@73e665f; remaining modules 9-12 OPEN)
Kind: ARCH
Author: architect (cycle 169)
Issue: #982

# ARCH-1: Apply the exact-contract docstring standard to `personal_index/**`

## Component
Every public function / method in `personal_index/**` (the package). This is a
systematic-application ticket: the standard itself is written in
`docs/CONTRACTS.md` (shipped in the same PR); this ticket assigns its
application to the implementer.

## Public contract (the standard — see docs/CONTRACTS.md)
A **contract docstring** states, in the function's own docstring, exactly what
the function does — no blanket adjectives, no over-promises. Three required
parts:
1. **Guard paths.** Every early-return / skip / falsy-input branch, stated as
   the exact value returned on that path. If there is no guard path, say so
   explicitly ("no guard path: always computes").
2. **Return-object fields.** The exact fields of the returned object, each with
   its computation. Never a blanket adjective like "computed" / "normalizes
   case" / "without breaking words" / "recommended".
3. **Side effects.** Any mutation, persistence, or I/O, or "no side effects".

**Pinning test** (one per function): asserts the **RETURNED OBJECT** (not
counters, not substrings, not the docstring wording) for BOTH the normal case
(all return fields with exact values) AND the guard-path input the docstring
now states (the skip / early-return / falsy-input case), so one returned object
pins both the main behavior and the guard path.

**Line-shift guard**: before committing, grep the WHOLE `tests/` tree for
line-number references (`lineno` / `getsource` / `_get_source_lines` /
`_method_line_span`); a LITERAL line-number pin is the real risk,
`inspect.getsource` / `_method_line_span` resolve by object/name via AST and
are safe.

## Acceptance criteria
- Every public function in `personal_index/**` has a contract docstring
  (parts 1-3 above).
- Every contract docstring has ONE pinning test asserting the returned object
  for normal + guard input.
- The local gate (pytest + ruff + mypy) is green.
- `docs/CONTRACTS.md` is the single reference for the standard.

## Pinning tests to add
One per target function (normal + guard input), asserting the returned object.

## Docs page it updates
`docs/CONTRACTS.md` (the standard, shipped in the same PR as this ticket).

## Module priority order (what remains unswept)
Apply the standard in this order (highest-value / most-drifted first). The
"already fixed" list from the last old-style briefing (cycles 155-168) is
excluded — do NOT re-pick those:
1. `content_validator` (rules.py `ValidationRule.validate` -> ARCH-5;
   quality.py `check_batch` / `filter_by_quality`; schema.py is already swept).
2. `index` (`SearchIndex.add_page` -> ARCH-4; `search` blanket docstring).
3. `models` (`PipelineStats` docstring + the API_REFERENCE.md field drift ->
   ARCH-3; `Interest.matches` / `score`; `CrawledPage.from_dict` guard).
4. `content_scoring` (`rank` — verify sort key / truncation; `_build_score`
   may already be claimed as issue #972 — re-verify before re-ticketing).
5. `content_dedup` (already swept 163-166; verify no residual blanket
   docstrings).
6. `cache` (`LRUCache` / `TTLCache` / `CacheDecorator` — verify).
7. `content_timeline` (verify the ordering-asymmetry pinning tests).
8. `content_summarizer` (already swept 155-156; verify).
9. `importer` (already swept 157-162; verify).
10. `content_categorizer` (already swept 160-162, 189; verify).
11. `analytics` (already swept 167-169; verify).
12. `app` (already swept 168; verify).

NOTE: re-verify each candidate against `gh issue list` + `git ls-tree
origin/main tickets/` before re-ticketing — a parallel run may have already
claimed it.
