# ARCH-95: `setup_logging` silently coerces an unknown level string to INFO instead of raising

Status: IMPLEMENTED #1561@c628267
Component: personal_index/logging_config.py
Issue: #1484

## Symptom

`setup_logging` (line 9) accepts a `level: str` argument and resolves it at
line 18:

    numeric_level = getattr(logging, level.upper(), logging.INFO)

The `getattr` third argument is a **silent default**: if `level.upper()` is not
a real attribute of the `logging` module, the expression falls back to
`logging.INFO` with no error and no log message. So a caller that passes a
typo or a level the module does not define — `"WARNIN"`, `"VERBOSE"`,
`"TRACE"`, `"CRITICALX"`, `"DEBUGG"`, or even an empty string `""` (whose
`.upper()` is `""`, not a logging attribute) — gets `INFO` logging with no
signal that their requested level was ignored.

This is a lossy contract: the function's signature advertises `level: str` as
if any string is honored, but the body only honors the exact set of
`logging` module attributes (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`,
plus `NOTSET`, `FATAL`, `CRIT`, `WARN`, `ERR`, `LVL` aliases). Every other
string is silently downgraded to `INFO`.

The existing test (`tests/test_logging_config.py`) pins only the valid levels
(`test_default_setup` → INFO, `test_verbose_setup` → DEBUG, `test_custom_level`
→ WARNING). It does **not** pin the unknown-level fallback, so the lossy
behavior is an untested invariant: a future refactor that "fixes" the fallback
to raise would pass the current suite, and a caller relying on the silent
fallback would break with no test to catch it.

## Evidence

- `setup_logging` line 18: `numeric_level = getattr(logging, level.upper(),
  logging.INFO)` — the third `getattr` argument is the silent default.
- `setup_logging` lines 15-16: `if verbose: level = "DEBUG"` — the `verbose`
  path is safe (it hard-codes a valid level), so the hole is only reachable
  via the `level` argument when `verbose` is falsy.
- `tests/test_logging_config.py` lines 12-25: the three level tests use only
  `INFO` (default), `DEBUG` (via `verbose=True`), and `WARNING` (via
  `level="WARNING"`). No test passes an unknown level string, so the fallback
  branch (line 18's default argument) is never exercised.
- `logging` module: `getattr(logging, "VERBOSE")` is `logging.INFO` (the
  default), confirming the silent coercion; `getattr(logging, "TRACE")` is
  likewise `logging.INFO`.

## Why it matters

A logging configuration function that silently ignores a mis-spelled level is
a footgun: a caller who types `setup_logging(level="WARNIN")` to quiet the
console gets `INFO` (noisier than intended) with no error, and the mis-configuration
surfaces only as "why is my log noisier than I asked for?" — with no stack
trace pointing at the typo. The contract should be fail-loud: an unrecognized
level is a caller bug and should raise, not be silently coerced.

## Proposed fix (implementer)

Minimal additive fix at line 18: validate the level before use and raise on an
unknown value. Concretely, replace the silent `getattr` default with an
explicit lookup that raises:

    numeric_level = getattr(logging, level.upper(), None)
    if numeric_level is None or not isinstance(numeric_level, int):
        raise ValueError(f"Unknown logging level: {level!r}")

This preserves every currently-valid input (`"INFO"`, `"DEBUG"`, `"WARNING"`,
`"ERROR"`, `"CRITICAL"`, and the `logging` aliases `WARN`/`ERR`/`CRIT`/`FATAL`/
`NOTSET`) unchanged, and turns the unknown-level path from a silent `INFO`
coercion into a `ValueError` naming the offending string. The `verbose=True`
path is unaffected (it hard-codes `"DEBUG"` before line 18).

## Acceptance criteria

1. `setup_logging(level="INFO")`, `setup_logging(level="DEBUG")`,
   `setup_logging(level="WARNING")`, `setup_logging(level="ERROR")`,
   `setup_logging(level="CRITICAL")` still set the `personal_index` root
   logger to the matching `logging` level (no behavior change for valid
   levels).
2. `setup_logging(level="VERBOSE")` (and any other unknown string, e.g.
   `"TRACE"`, `"WARNIN"`, `""`) raises `ValueError` whose message contains the
   offending string, and does **not** leave the root logger at `INFO`.
3. `setup_logging(verbose=True)` still forces `DEBUG` regardless of `level`
   (the `verbose` override at lines 15-16 is preserved).
4. The idempotent handler reset (line 24) and the conditional file handler
   (lines 36-41) are unchanged by the fix.

## Pinning tests to add (tests/test_logging_config.py)

- `test_unknown_level_raises`: call `setup_logging(level="VERBOSE")` and assert
  `pytest.raises(ValueError, match="VERBOSE")`. This pins the fail-loud
  contract for the unknown-level path (the guard/early-return input the
  corrected contract now states).
- `test_valid_levels_still_honored`: parametrize over
  `["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]`, call
  `setup_logging(level=lv)` for each, and assert
  `logging.getLogger("personal_index").level == getattr(logging, lv)`. This
  pins that the fix did not regress any valid level (the normal case alongside
  the guard path).

## Docs update (same PR)

`docs/logging_config.md` (new spec page) documents the public surface, the
invariants (verbose override, upper-case lookup, idempotent handler reset,
conditional file handler), and calls out this hole under "Known contract
holes"; `docs/README.md` gains the index entry.

## Self-review checklist

- [x] Component named (personal_index/logging_config.py)
- [x] Public contract stated (setup_logging signature + level-resolution behavior; get_logger)
- [x] file:line evidence (line 18 silent getattr default; lines 15-16 verbose override; tests 12-25 pin only valid levels)
- [x] Proposed fix (explicit lookup + ValueError on unknown level)
- [x] Acceptance criteria (4)
- [x] Pinning tests to add (2: unknown-level raises + valid-levels still honored)
- [x] Matching docs/ page update in the SAME PR (docs/logging_config.md + README index)
- [x] Witness check: the existing test pins only valid levels (INFO/DEBUG/WARNING); the unknown-level fallback branch is NOT pinned, so this is a genuine untested invariant, not a doc-only over-promise
