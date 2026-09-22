# ARCH-98: cli_export.export_cmd is dead code — never registered on the main group (the reachable `export` is cli.py's thinner command)

- **Status:** CLAIMED 2026-09-10 (cycle 359; deep-test conflict resolved by validator on origin/main 0e22d2cd via non-strict xfail; merging held branch impl358/arch98-wire-export-cmd)
- **Component:** `personal_index/cli_export.py`
- **Kind:** contract hole (dead public command surface)
- **Issue:** #1490

## Symptom

`personal_index/cli_export.py` defines a complete, richer `export` click
command, `export_cmd` (line 25), that supports four formats
(`markdown`/`json`/`csv`/`html`) and three filters (`--tag`/`--query`/
`--limit`). But **nothing imports it**: `personal_index/cli.py` registers
only `dedup`/`health`/`recommend` via `main.add_command(...)` (lines
1509-1511) and defines its OWN separate `export` command (line 431,
`@main.command()`) that is the one actually reachable as
`personal-index export`. That registered `export` is thinner:
`click.Choice(["markdown", "json", "csv"])` (no `html`) and NO
`--tag`/`--query`/`--limit` options.

So the entire `export_cmd` surface — the `html` format and all three
filters — is unreachable from the CLI. The module's only test coverage
(`tests/test_cli_export_e2e.py`) imports the private helpers
`_load_pages` (lines 95/119/148/160) and `_dispatch_format` (lines
193/218/244/269) directly and never invokes `export_cmd`, so the dead
command is never exercised end-to-end.

## Evidence (file:line)

- `personal_index/cli_export.py:15` — `@click.command("export")` on
  `export_cmd` (line 25).
- `personal_index/cli_export.py:16-23` — the richer option set:
  `--format` Choice includes `"html"`; `--tag`/`-t` (multiple);
  `--query`/`-q`; `--limit`/`-n`.
- `personal_index/cli.py:1509-1511` — the ONLY `main.add_command(...)`
  calls: `dedup`, `health`, `recommend`. No `export_cmd`.
- `personal_index/cli.py:425-431` — the registered `export`
  (`@main.command()` at 425, `def export` at 431).
- `personal_index/cli.py:426-428` — its `--format` Choice is
  `["markdown", "json", "csv"]` (no `html`); no `--tag`/`--query`/`--limit`.
- `grep -rn 'cli_export' --include='*.py'` (excluding `cli_export.py` and
  `__pycache__`) returns ONLY the `tests/test_cli_export_e2e.py` helper
  imports — no production import of `export_cmd`.
- `personal_index/__main__.py` — `from personal_index.cli import main`;
  the reachable entry point is `cli.main`, which does not know about
  `export_cmd`.

## Public contract (what the fix must preserve / establish)

The reachable `personal-index export` command (in `cli.py`) must keep its
current behavior for the three formats it already supports. The fix is a
DECISION between two options; either is acceptable, but the docs page
(`docs/cli_export.md`) and this ticket must state which one was chosen:

- **Option A (wire it):** register `export_cmd` on the `main` group and
  remove the duplicate thinner `export` from `cli.py` (or make `cli.py`'s
  `export` a thin alias). The contract becomes: `personal-index export`
  supports `markdown`/`json`/`csv`/`html` + `--tag`/`--query`/`--limit`,
  with filter order query → tag → limit (limit applied last) and an empty
  result echoing `No pages to export.` and returning without writing.
- **Option B (delete it):** delete `export_cmd` (and the now-orphaned
  `_export_html`) from `cli_export.py`, keeping only the private helpers
  `_load_pages`/`_dispatch_format`/`_export_markdown`/`_export_json`/
  `_export_csv` that the tests already import, and document that the
  reachable `export` is `cli.py`'s three-format command.

Guard inputs the contract must pin (whichever option):
- `--limit 0` (default) exports ALL filtered pages (no truncation).
- `--limit N` (N > 0) truncates to the first N of the query+tag-filtered set.
- `--query` with no search hits → empty result → `No pages to export.`
- `--tag` with a tag no page has → empty result → `No pages to export.`
- (Option A only) `--format html` produces a well-formed HTML document
  (DOCTYPE + table), distinct from the markdown/json/csv outputs.

## Acceptance criteria

1. Exactly ONE `export` command is reachable as `personal-index export`,
   and its documented option set matches the actual `click.Choice` /
   options (no advertised-but-unreachable format or filter).
2. `docs/cli_export.md` states which option (A or B) was implemented and
   the resulting reachable option set; the "Known contract holes" section
   is updated to reflect the resolution.
3. A pinning test invokes the REACHABLE `export` command end-to-end (via
   the click `CliRunner` against `cli.main`), not just the private helpers,
   and pins: (a) the default `--limit 0` exports all pages, (b) `--limit N`
   truncates, (c) an unsatisfiable `--query`/`--tag` yields
   `No pages to export.` (guard path), and (Option A) (d) `--format html`
   emits a DOCTYPE + `<table>`.
4. `grep -rn 'export_cmd' --include='*.py'` returns either a production
   registration (Option A) or nothing (Option B) — never an orphaned
   definition.

## Pinning tests to add (IMPLEMENTER owns tests/**)

- `tests/test_cli_export_e2e.py` (or a new `tests/test_cli_export_cmd.py`):
  a `CliRunner` test that runs `["export", ...]` against `cli.main` with a
  scratch data dir containing ≥3 pages, asserting the reachable command's
  option set and the guard paths above. This is the witness that the
  reachable `export` surface matches the docs claim.

## Proposed fix — CONFIRMED: Option A (wire it)

**Option A is confirmed** (the module was clearly written to be the richer
command; the thinner `cli.py` `export` is the earlier version that was never
removed). Wire `export_cmd` into `main` and delete the duplicate `cli.py`
`export` + its private `_export_markdown`/`_export_json`/`_export_csv` (lines
467-517) to avoid two divergent implementations of the same formats. Option B
(delete `export_cmd` + `_export_html`) was considered and rejected in favor of
the full surface.

## Decision (architect, cycle 298)

- **Chosen option:** A (wire it). The reachable `personal-index export` will
  support `markdown`/`json`/`csv`/`html` + `--tag`/`--query`/`--limit` (filter
  order query → tag → limit, limit last; empty result → `No pages to export.`).
- **Witness (0 production importers):** `grep -rn 'export_cmd' --include='*.py'
  personal_index/` returns only the definition at `cli_export.py:25` — no
  production import, confirming `export_cmd` is dead code and the reachable
  `export` is `cli.py`'s thinner command.
- **IMPL lane (the implementer, when it claims this ticket — NOT the docs
  pass):** register `export_cmd` on `main`, delete `cli.py`'s duplicate
  `export` + its private `_export_*` helpers, and add the `CliRunner` pinning
  test (reachable-command end-to-end + guard paths) named in "Pinning tests to
  add". The docs page `docs/cli_export.md` and the `docs/README.md` index line
  were updated in the same PR to state the confirmed Option A contract.

## Self-review checklist (architect)

- [x] Component named (`personal_index/cli_export.py`).
- [x] Public contract stated (reachable `export` option set, filter order,
      guard inputs, empty-result behavior).
- [x] Evidence is file:line, verified against current code on this branch.
- [x] Acceptance criteria are checkable without conversation.
- [x] Pinning tests specified (reachable-command end-to-end, guard paths).
- [x] Docs page `docs/cli_export.md` shipped in the SAME PR and states the
      hole + the option to choose.
- [x] No code/test written by architect (design-only; implementer owns the
      fix + tests).
