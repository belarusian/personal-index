# TICKET-497: signal_coverage docstring over-promises a codemap `tests` fallback that does not exist

Status: OPEN
Issue: #848
Module: personal_index/cycle_signals.py
Function: signal_coverage
Class: (b) docstring drift (over-promise)

## Symptom
`signal_coverage`'s docstring claims:
    "Falls back to codemap `tests` field if no test directory found."
The body performs NO such fallback. It only matches test files in `test_dir`
(glob `test_dir/test_*.py`) against module short names. When `test_dir` is None
or not an existing directory, `covered_modules` stays empty and the function
returns `modules_with_tests: 0`, `coverage_pct: 0.0` — the codemap `tests`
field is never consulted.

## Evidence (line)
- Docstring claim: personal_index/cycle_signals.py:510
  ("Falls back to codemap `tests` field if no test directory found.")
- Body: personal_index/cycle_signals.py:513-539 — `covered_modules` is only
  populated inside `if test_dir and Path(test_dir).is_dir():`; there is no
  reference to `m["tests"]` anywhere in the function.
- Probe:
    signal_coverage([{'name':'pkg.analytics','tests':3,...},
                     {'name':'pkg.beta','tests':0,...}], None)
      -> {'total_modules': 2, 'modules_with_tests': 0, 'modules_without_tests': 2,
          'coverage_pct': 0.0, 'test_dir_used': None}
  (analytics has tests=3 but is reported as uncovered.)

## Minimal additive fix
Reword the docstring to state the EXACT contract: coverage is estimated ONLY by
matching `test_dir/test_*.py` filenames to module short names; when `test_dir`
is None or not an existing directory, no test files are matched and coverage is
reported as 0 (the codemap `tests` field is NOT consulted). Add ONE pinning
behavior test that pins the corrected claim against the returned dict, including
the guard path (no test dir -> coverage_pct 0.0 even when a module has tests>0)
alongside the normal case (a real test dir -> the matching module is counted).
