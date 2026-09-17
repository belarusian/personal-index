# ARCH-94: `generate` (full pipeline) never attributes per-source-module test counts — the test bar chart and S1 signal read a binary 0/1, not a real count

Status: CLOSED (validator cycle 258 @ main 2ddeccb; generate() now calls _attribute_test_counts after the test scan (line 1366); pinning tests green: tests/test_docs_generator.py + tests/deep/test_docs_generator_adversarial.py; adversarial per-module count tests added TestGenerateAttributesTestCounts; [was IMPLEMENTED #1560@56dbfe3 impl321 cycle 321])
Component: personal_index/docs_generator.py
Issue: #1481

## Symptom

The module exposes two public entry points that build the same `DashboardData`
but disagree on what a source module's `test_count` means:

- `generate_fast` (line 1398) calls `_attribute_test_counts(modules,
  test_modules)` (line 1408). That helper (line 1377) strips the `test_` prefix
  from each test module's stem and adds the test module's AST-derived
  `test_count` (the real number of `test_*` functions/methods) onto the matching
  source module. So under `generate_fast`, a source module's `test_count` is a
  **real count**.
- `generate` (line 1344, the full pipeline) does **NOT** call
  `_attribute_test_counts`. Its per-source-module `test_count` comes only from
  `run_pytest` (line 276), which at line 289 does
  `mod.test_count = max(mod.test_count, 1)` — a **binary 0/1** flag meaning
  "this module's name appeared on a passing pytest summary line", not how many
  tests it has.

Both `_render_test_bars` (line 581) and `_signal_no_tests` (line 461, the S1
"no tests" signal) read the per-source-module `test_count`. So the full-pipeline
dashboard renders every tested module with a bar of width `1/max*100` and a
literal count of `1`, and S1 can flag a module as "no tests" even though
`tests/test_<stem>.py` exists and was scanned into `test_modules` — its count
simply never flows back to the source module.

The aggregate `total_tests` is correct in BOTH paths (it is the sum of
`test_count` over `test_modules`, computed in `_build_dashboard_data` line
1305), so the bug is invisible in the summary totals and only visible in the
per-module bar chart and the S1 signal.

## Evidence

- `generate` (lines 1344-1373): the full pipeline calls `scan_modules`,
  `run_ruff`, `run_mypy`, `run_pytest`, scans `tests/` into `test_modules`,
  `detect_dependencies`, `fetch_recent_commits`, then `_build_dashboard_data`
  and `_write_dashboard`. There is no call to `_attribute_test_counts` anywhere
  in the function body (grep for `_attribute_test_counts` in the file returns
  only the definition at line 1377 and the single call at line 1408 inside
  `generate_fast`).
- `run_pytest` line 289: `mod.test_count = max(mod.test_count, 1)` — the only
  place the full pipeline ever writes a per-source-module `test_count`, and it
  is clamped to 1.
- `_render_test_bars` (line 581) sorts modules by `test_count` and renders
  `int(test_count / max_tests * 100)` width + the literal `test_count`; with
  every tested module at 1, all bars collapse to the same minimal width.
- `_signal_no_tests` (line 461) flags a module when `test_count == 0` and it has
  functions; a module whose tests live in `tests/test_<stem>.py` but whose name
  did not appear on a passing pytest line (e.g. a skipped/errored run, or a
  summary line that names the test file rather than the source stem) is flagged
  "no tests" despite the test file existing.

## Why it matters

The dashboard's per-module test bar chart and the S1 "no tests" signal are the
two surfaces a reader uses to spot under-tested modules. Under the full
pipeline (the default `generate`), those surfaces are driven by a binary flag,
so (a) the bar chart is meaningless (every tested module shows `1`) and (b) S1
can both under-report (a tested module flagged as having no tests) and
over-report (a module with 50 tests shows the same bar as one with 1). The
aggregate `total_tests` masks the problem, so the defect is silent in the
summary and only visible in the per-module views.

## Proposed fix (implementer)

Minimal additive fix: make `generate` (line 1344) call
`_attribute_test_counts(modules, test_modules)` immediately after it scans
`tests/` into `test_modules` (after the `test_modules = scan_modules(test_root)`
line, before `_build_dashboard_data`), mirroring `generate_fast`. This makes the
per-source-module `test_count` a real count in both entry points, so the bar
chart and S1 signal become meaningful. `run_pytest`'s binary clamp (line 289)
can be left as-is (it only ever raises the count to at least 1, and
`_attribute_test_counts` adds the real count on top) or removed; the essential
change is the missing attribution call in `generate`.

## Acceptance criteria

1. `generate` (line 1344) calls `_attribute_test_counts(modules, test_modules)`
   after scanning `tests/` and before `_build_dashboard_data`, so a source
   module's `test_count` reflects the real number of `test_*` functions/methods
   in its `tests/test_<stem>.py` file.
2. After the fix, for a module with N tests in its test file, the full-pipeline
   dashboard's per-module bar shows count N (not 1), matching what
   `generate_fast` already produces.
3. The aggregate `total_tests` is unchanged (still the sum over `test_modules`),
   so the summary totals are unaffected.
4. S1 (`_signal_no_tests`) no longer flags a module that has a matching
   `tests/test_<stem>.py` with at least one `test_*` function.

## Pinning tests to add (tests/test_docs_generator.py)

- `test_generate_attributes_test_counts_like_fast`: build a small source tree
  with one module `foo.py` (a couple of functions) and a `tests/test_foo.py`
  with 3 `test_*` functions; monkeypatch `run_ruff`/`run_mypy`/`run_pytest` to
  no-ops (or a passing summary) so the only `test_count` source is the test-file
  scan; call `generate(root, output)` and assert the resulting `DashboardData`
  gives `foo` a per-module `test_count == 3` (not 1). This pins the missing
  attribution call in the full pipeline.
- `test_generate_and_fast_agree_on_per_module_test_counts`: same fixture, call
  both `generate` and `generate_fast`, and assert the per-source-module
  `test_count` maps are equal. Pins the two entry points to the same contract.

## Docs update (same PR)

`docs/docs_generator.md` (new spec page) documents both entry points and calls
out this hole under "Known contract hole"; `docs/README.md` gains the index
entry.

## Self-review checklist

- [x] Component named (personal_index/docs_generator.py)
- [x] Public contract stated (both entry points, per-module vs aggregate test_count)
- [x] file:line evidence (generate 1344, run_pytest 289, _attribute_test_counts 1377/1408, _render_test_bars 581, _signal_no_tests 461)
- [x] Proposed fix (add the missing _attribute_test_counts call in generate)
- [x] Acceptance criteria (4)
- [x] Pinning tests to add (2)
- [x] Matching docs/ page update in the SAME PR (docs/docs_generator.md + README index)
- [x] Witness check: generate_fast already attributes (line 1408); generate does not — the asymmetry is the hole
- CLOSED (architect, cycle 311): contract VERIFIED by the validator (PR #1560); docs reconciled; closing the VERIFIED pile.
