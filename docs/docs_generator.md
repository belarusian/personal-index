# `personal_index.docs_generator` — spec

Generate a self-contained HTML dashboard + machine-readable codemap JSON for
the personal-index project. Scans every `.py` file under a root via AST,
optionally shells out to `ruff` / `mypy` / `pytest` / `git log`, aggregates the
results into a `DashboardData` dataclass, and renders (1) a dark-terminal HTML
dashboard with an embedded JSON codemap `<script>` block and (2) a sibling
`*_metadata.json` codemap for AI consumption. No crawl, no network fetch of
content — it only inspects the local source tree and shells out to local tools.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/docs_generator.py` — the *generator* that produces
> `docs_dashboard.html` + `docs_dashboard_metadata.json`. It is **distinct
> from** `personal_index/publish_dashboard.py` (the *publisher* CLI that ships
> those artifacts to `belarusian/search`, covered by `publish_dashboard.md`)
> and from `personal_index/cycle_signals.py` (the signal extractor this module
> imports `build_tree` from, covered by `cycle-signals.md`).
> `tests/test_docs_generator.py:10` does
> `from personal_index.docs_generator import (...)`;
> `tests/deep/test_docs_generator_adversarial.py:30` does the same.

## Public surface

Line numbers refer to `personal_index/docs_generator.py`.

### Dataclasses

| symbol | line | fields |
|--------|------|--------|
| `FunctionInfo` | 25 | `name, line, docstring="", is_async=False, is_method=False, parent_class=""` |
| `ClassInfo` | 36 | `name, line, docstring="", bases=[], methods=[]` |
| `ModuleInfo` | 46 | `filepath, module_name, line_count=0, classes=[], functions=[], imports=[], docstring="", ruff_errors=[], ruff_warnings=[], mypy_errors=[], test_count=0, status="clean"` (`status` ∈ `clean`/`warning`/`error`) |
| `CommitInfo` | 63 | `sha_short, message, author, date` |
| `DashboardData` | 72 | `modules, total_modules, total_lines, total_test_lines, total_classes, total_functions, total_tests, total_ruff_errors, total_ruff_warnings, total_mypy_errors, dependency_graph, test_results, commits, test_module_names` + `to_dict()` (line 89, `asdict`) |

### Scanning / tooling

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `scan_modules` | 124 | `(root: str) -> list[ModuleInfo]` | `os.walk(root)`, parse every `.py` (sorted) via `_parse_module`; returns the list |
| `_parse_module` | 193 | `(filepath: str) -> ModuleInfo` | Reads source (`errors="replace"`); on `OSError` → `status="error"`; `line_count = max(source.count("\n"), 1)`; on `SyntaxError` → appends to `ruff_errors`, `status="error"`; else fills docstring/imports/functions and calls `_count_tests` |
| `_count_tests` | 182 | `(info: ModuleInfo) -> None` | Increments `info.test_count` for every top-level `test_*` function and every `test_*` method (AST-derived, not run) |
| `run_ruff` | 224 | `(modules: list[ModuleInfo]) -> None` | `python -m ruff check --output-format=text .` (timeout 60); matches each output line to a module by `mod.filepath in line`; lines with `error`/`F`/`E` → `ruff_errors`, else `ruff_warnings`; sets `status` to `error`/`warning` |
| `run_mypy` | 253 | `(modules: list[ModuleInfo]) -> None` | `python -m mypy .` (timeout 120); skips `: note:` lines; matches by `mod.filepath in line` → `mypy_errors`; sets `status="error"` |
| `run_pytest` | 276 | `(modules: list[ModuleInfo]) -> str` | `python -m pytest --tb=short -q` (timeout 120); returns the combined stdout+stderr; for each summary line that names a module and contains `PASSED`/`passed`, sets `mod.test_count = max(mod.test_count, 1)` — i.e. a **binary 0/1**, never a real count |
| `detect_dependencies` | 299 | `(modules: list[ModuleInfo]) -> dict[str, list[str]]` | For each module, an import is a dependency if it equals a known module name or is a dotted prefix/suffix of one (and is not the module itself); returns `module -> sorted(set(deps))` |
| `fetch_recent_commits` | 318 | `(n: int = 20) -> list[CommitInfo]` | `git log -<n> --format=%h\|%s\|%an\|%ad --date=short` (timeout 10); parses 4-field lines; returns `[]` on timeout/missing git |

### Rendering / output

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `_compute_signals` | 533 | `(data: DashboardData) -> dict` | Computes `S1_no_tests` (per-module `test_count == 0` and has functions, skipping `cli_*`/`test_*`/`__init__`/`__main__`), `S2_oversized` (`line_count >= 200` and `fc >= 15`), `S5_errors`, `S6_coverage` (stem-match of `test_module_names` against module short names) |
| `_render_test_bars` | 581 | `(modules: list) -> str` | Sorts modules by `test_count` desc; renders one bar per module with width `int(test_count / max_tests * 100)` and the literal `test_count` — **driven by per-module `test_count`** |
| `generate_dashboard` | 713 | `(data: DashboardData, output_path: str) -> None` | Computes signals, renders module rows / dep tree / test bars / commit rows / heat rows, embeds a `<script type="application/json" id="codemap-metadata">` block, writes `output_path` |
| `generate_metadata_json` | 424 | `(data: DashboardData, output_path: str) -> str` | Imports `build_tree` from `cycle_signals`; writes `<output_path stem>_metadata.json` with `generated_at`, `summary` (totals), `tree_summary`, `modules`, `dependency_graph`, `commits`; returns the JSON path |
| `_build_dashboard_data` | 1305 | `(modules, test_modules, test_summary, dep_graph, commits) -> DashboardData` | Sums `line_count`/`test_count`/classes/functions/errors across `modules` (source) and `test_modules` (tests); `total_tests = sum(m.test_count for m in test_modules)` |
| `_write_dashboard` | 1330 | `(data, output: str) -> str` | Calls `generate_dashboard` then `generate_metadata_json`; prints a summary; returns `output` |
| `generate` | 1344 | `(root="personal_index", output="personal_index/docs_dashboard.html") -> str` | **Full pipeline:** `scan_modules(root)` → `run_ruff` → `run_mypy` → `run_pytest` → scan `tests/` into `test_modules` → `detect_dependencies` → `fetch_recent_commits(20)` → `_build_dashboard_data` → `_write_dashboard`. **Does NOT call `_attribute_test_counts`.** |
| `_attribute_test_counts` | 1377 | `(modules: list, test_modules: list) -> None` | For each test module whose short stem starts with `test_`, strips `test_` and adds that test module's `test_count` to the source module whose short stem matches (first match, `break`) |
| `generate_fast` | 1398 | `(root="personal_index", output="personal_index/docs_dashboard.html") -> str` | **Fast pipeline:** `scan_modules(root)` → scan `tests/` into `test_modules` → **`_attribute_test_counts(modules, test_modules)`** → `detect_dependencies` → `fetch_recent_commits(20)` → `_build_dashboard_data(..., "", ...)` → `_write_dashboard`. Skips ruff/mypy/pytest. |

## Invariants

- `line_count` is `max(source.count("\n"), 1)` — a non-empty file always reports
  ≥ 1 line; an unreadable file reports `line_count=0` with `status="error"`.
- `total_lines = total_source_lines + total_test_lines` where
  `total_source_lines = data.total_lines - data.total_test_lines` (re-derived in
  `generate_metadata_json` and `generate_dashboard`).
- `total_tests` is the sum of `test_count` over **test modules** (the `tests/`
  scan), not over source modules.
- `status` is a three-valued enum (`clean`/`warning`/`error`); `run_ruff` and
  `run_mypy` only ever *raise* it (error > warning > clean), never lower it.

## Known contract hole (ARCH-94)

The two public entry points disagree on whether per-source-module `test_count`
is a real count or a binary flag:

- `generate_fast` calls `_attribute_test_counts` (line 1408), so each source
  module's `test_count` becomes the **real number of `test_*` functions/methods**
  in its matching `tests/test_<stem>.py` file.
- `generate` (the full pipeline) never calls `_attribute_test_counts`. Its
  per-source-module `test_count` comes only from `run_pytest` (line 289), which
  sets `mod.test_count = max(mod.test_count, 1)` — a **binary 0/1** that says
  "this module's name appeared on a passing pytest line", not how many tests it
  has.

Because `_render_test_bars` (line 581) and `_signal_no_tests` (line 461, S1)
both read the per-source-module `test_count`, the full-pipeline dashboard shows
every tested module with a bar of width `1/max*100` and count `1`, and S1 can
flag a module as "no tests" even though `tests/test_<stem>.py` exists and was
scanned into `test_modules` (its count just never flows back to the source
module). The aggregate `total_tests` is correct in both paths (it sums
`test_modules`), so the bug is invisible in the summary and only visible in the
per-module bar chart and the S1 signal. See `tickets/ARCH-94.md`.
