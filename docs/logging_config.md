# `personal_index.logging_config` — spec

Configure logging for the `personal_index` package. Two public functions:
`setup_logging` (idempotently re-wires the `personal_index` root logger with a
console handler and an optional file handler) and `get_logger` (returns a
child logger namespaced under `personal_index.<name>`). No state is persisted;
the only side effects are on the in-process `logging` module.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/logging_config.py` — the *logging* configuration helper.
> It is **distinct from** `personal_index/cli.py` (the Click CLI entry point,
> which exposes a `--verbose` flag but does **not** call `setup_logging`) and
> from `personal_index/__main__.py` (the `python -m personal_index` shim that
> just forwards to `cli.main`). `tests/test_logging_config.py:6` does
> `from personal_index.logging_config import get_logger, setup_logging`.

## Public surface

Line numbers refer to `personal_index/logging_config.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `setup_logging` | 9 | `(level: str = "INFO", verbose: bool = False, log_file: str \| None = None) -> None` | Re-wires the `personal_index` root logger (see invariants). Returns `None`. |
| `get_logger` | 45 | `(name: str) -> logging.Logger` | `logging.getLogger(f"personal_index.{name}")` — a child logger under the `personal_index` namespace. |

## Invariants

- **`verbose` overrides `level`** (line 15-16): if `verbose` is truthy,
  `level` is forced to `"DEBUG"` regardless of the `level` argument.
- **Level is upper-cased then looked up** (line 18):
  `numeric_level = getattr(logging, level.upper(), logging.INFO)`.
- **Idempotent handler reset** (line 24): `root_logger.handlers.clear()` runs
  before handlers are (re)attached, so calling `setup_logging` twice does not
  stack duplicate handlers.
- **Console handler always attached** (lines 26-31): a `StreamHandler` with
  the `%(asctime)s - %(name)s - %(levelname)s - %(message)s` formatter is
  always added, at `numeric_level`.
- **File handler is conditional** (lines 36-41): only when `log_file` is
  truthy. The parent directory is created with
  `Path(log_file).parent.mkdir(parents=True, exist_ok=True)` (line 38) before
  the `FileHandler` is opened, so a missing directory does not raise.
- **Both handlers share one formatter and one level** (lines 27, 31, 40):
  the same `Formatter` instance and the same `numeric_level` are applied to
  the console and file handlers.

## Known contract holes

- **Silent unknown-level fallback (ARCH-95):** line 18 uses
  `getattr(logging, level.upper(), logging.INFO)`, so an unrecognized level
  string (e.g. `"VERBOSE"`, `"TRACE"`, `"CRITICALX"`, or a typo like
  `"WARNIN"`) is **silently coerced to `logging.INFO`** instead of raising.
  The caller has no signal that their requested level was ignored. The
  existing test (`tests/test_logging_config.py`) pins only the valid levels
  (`INFO`/`DEBUG`/`WARNING`) and does **not** pin the unknown-level fallback,
  so this lossy behavior is an untested invariant. See `tickets/ARCH-95.md`.
- **Unwired in the CLI (observation, not ticketed):** `setup_logging` and
  `get_logger` are referenced **only** by `tests/test_logging_config.py`.
  `personal_index/cli.py` exposes a `--verbose` flag (line 52) and stores it
  in `ctx.obj["verbose"]` (line 69), but no `cli_*.py` command consumes that
  flag or calls `setup_logging` / `logging.basicConfig`. The module is
  therefore dead in the product sense: the CLI's `--verbose` flag does not
  actually configure logging. This is recorded here as a known gap; it is not
  the subject of ARCH-95 (which is the level-fallback contract hole).
