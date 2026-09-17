# `personal_index.cycle_signals` — spec

Cycle signal extractor. Reads a `codemap.json` and emits heuristic signals
(S1–S6) that scope the next audit cycle. Pure functions over the codemap dict
plus a small CLI (`main`). No network, no writes — the only I/O is reading the
codemap file(s) and the optional `test_dir` for coverage estimation.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/cycle_signals.py` — the codemap signal extractor
> (`build_tree` / `signal_*` / `extract` / `format_for_auditor`). It is
> **distinct from** `personal_index/cycle_log.py` (the cycle-log reader/writer,
> if present) and from the `ai/cycle-*.md` gate log (a file, not a module).
> The single test file imports this module: `tests/test_cycle_signals.py:10`
> does `from personal_index import cycle_signals`.

## Public surface

All public functions are module-level (no classes). Line numbers refer to
`personal_index/cycle_signals.py`.

| function | line | signature | returns |
|----------|------|-----------|---------|
| `build_tree` | 256 | `(modules: list[dict]) -> dict` | nested tree node dict |
| `format_tree` | 270 | `(tree: dict, max_depth: int = 2, max_lines: int = 50) -> str` | pruned tree text |
| `load_codemap` | 344 | `(path: str) -> dict` | parsed codemap dict (or `sys.exit(1)`) |
| `signal_no_tests` | 364 | `(modules: list[dict]) -> list[dict]` | S1 list |
| `signal_oversized` | 394 | `(modules, line_threshold=200, func_threshold=15) -> list[dict]` | S2 list |
| `signal_dead_code` | 446 | `(modules, dep_graph: dict) -> list[dict]` | S3 list |
| `signal_duplicates` | 461 | `(modules) -> list[dict]` | S4 list |
| `signal_errors` | 488 | `(modules) -> list[dict]` | S5 list |
| `signal_coverage` | 507 | `(modules, test_dir: str \| None = None) -> dict` | S6 dict |
| `extract` | 552 | `(codemap_path, prev_codemap_path=None, test_dir=None) -> dict` | full signals dict |
| `format_for_auditor` | 653 | `(signals: dict) -> str` | scoped auditor prompt |
| `main` | 666 | `() -> None` | CLI entry (argparse) |

### `build_tree` (line 256)

Groups modules into a hierarchical tree by dotted package path. Each node has:
`name`, `stats` (`{lines, functions, classes, errors, warnings, modules}`),
`signals` (sorted list of active tags), and `modules` (the node's own module
names) whenever the node has any. A node that is BOTH a module (its own
`__init__.py` / package file has functions, so it appears in `node["modules"]`)
AND has children (a subpackage) carries BOTH its own `modules` list and its
`children` — the own-module entry is never dropped (ARCH-90, confirmed
Option b). `_node_to_dict` (line 205) populates `signal_modules` from
`node["modules"]` unconditionally and emits `result["modules"]` whenever it is
non-empty, so `stats.modules` (own + descendants) always agrees with the
visible module listing.

**Witness:** the implementer pinning tests
`tests/test_cycle_signals.py::test_package_with_children_keeps_own_module`
(the `pkg.sub` + `pkg.sub.beta` case: `sub["modules"] == ["pkg.sub"]`,
`sub["children"]["beta"]["modules"] == ["pkg.sub.beta"]`,
`sub["stats"]["modules"] == 2`) and
`tests/test_cycle_signals.py::test_leaf_node_modules_unchanged` (guard path: a
leaf node with no children still lists its own modules) pin the confirmed
contract — a package node keeps its own module alongside its children, and a
leaf node's behavior is unchanged.

### `format_tree` (line 270)

Pruned tree summary for LLM consumption. Shows top-level packages, expands
only nodes that carry signals, collapses clean subtrees into a single line,
and hard-caps output at `max_lines`. `max_depth` bounds expansion depth.

### `load_codemap` (line 344)

Reads and parses a codemap JSON file. Error paths (all `sys.exit(1)` with a
`[signal] ERROR:` line on stderr): file not found, invalid JSON
(`json.JSONDecodeError`), or top-level value not a dict.

### Signals S1–S6

- **S1 `signal_no_tests` (364):** modules with `tests == 0` and
  `functions > 0`, excluding scaffolding (`__init__`, `__main__`) and
  `cli_*` / `test_*` prefixes. `severity` is `high` if `lines > 100` else
  `medium`. Sorted by `lines` desc.
- **S2 `signal_oversized` (394):** modules with `lines >= line_threshold`
  (default 200) AND `functions >= func_threshold` (default 15). `severity`
  `critical` if `lines > 400` else `high`. Sorted by `lines` desc.
- **S3 `signal_dead_code` (446):** modules with no static incoming import
  (from `dep_graph` values or each module's `imports` field) that still have
  logic (`functions > 0` or `classes > 0`), excluding `__init__`/`__main__`.
  `confidence` is always `"low"` — dynamic dispatch means these are candidates
  only; the outer loop must verify before acting. Sorted by `lines` asc.
- **S4 `signal_duplicates` (461):** modules whose underscore-stripped,
  12-char-truncated stem collides (≥2 distinct short names per stem).
  Sorted by `count` desc.
- **S5 `signal_errors` (488):** modules with `ruff_errors + mypy_errors +
  ruff_warnings > 0`. Sorted by `total` desc.
- **S6 `signal_coverage` (507):** coverage estimated ONLY by matching
  `test_dir/test_*.py` files to module short names (strip `test_`, match
  `short == stem` or `short == "_" + stem`). **No fallback** to the codemap
  `tests` field: when `test_dir` is `None` or not an existing directory,
  `modules_with_tests` is 0 and `coverage_pct` is 0.0. Returns
  `{total_modules, modules_with_tests, modules_without_tests, coverage_pct,
  test_dir_used}`.

### `extract` (line 552)

Orchestrates: `load_codemap` → `build_tree` → `_build_signals` (S1–S6) →
optionally `_add_coverage_delta` when `prev_codemap_path` is given.
`_detect_test_dir` auto-detects `tests/`, `../tests/`, `../../tests/` relative
to the codemap's parent when `test_dir` is not supplied.

**Silent-failure note:** `_add_coverage_delta` wraps `load_codemap(prev_path)`
in `try/except SystemExit: pass`, so a missing/malformed `--prev` codemap is
swallowed and the `previous`/`delta_pct` keys are simply absent — no warning.

### `format_for_auditor` (line 653) / `main` (line 666)

`format_for_auditor` renders the signals dict as a scoped auditor prompt
(tree + S5 + S1 + S2 + S3 + S4 + S6 sections). `main` is the CLI: positional
`codemap`, `--prev`, `--test-dir`, `--format {json,auditor,tree}`, `--depth`,
`--lines`. JSON output serializes sets to sorted lists.

## Invariants

- All `signal_*` functions are pure over their inputs (no I/O, no mutation of
  the input module dicts).
- `build_tree` output `stats.modules` at the root equals the number of
  non-root modules fed in (root package name is skipped).
- `signal_coverage` never consults the per-module `tests` field; coverage is
  file-matching only.
