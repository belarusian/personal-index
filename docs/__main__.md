# `personal_index.__main__` — spec

`personal_index/__main__.py` is the package entry point that makes
`python -m personal_index` work. It is 6 lines of thin glue: it imports the
click `main` group from `personal_index.cli` and calls it under the standard
`if __name__ == "__main__":` guard.

> **Module identity (entry-point disambiguation):** this page documents
> `personal_index/__main__.py` — the `python -m personal_index` entry point.
> It is distinct from the console-script entry point declared in the two
> packaging files (`pyproject.toml` `[project.scripts]` and `setup.py`
> `entry_points`), which install the `personal-index` command, and from
> `personal_index/cli.py:1514` (its own `if __name__ == "__main__": main()`
> block, reachable only via `python personal_index/cli.py`). All three paths
> funnel into the SAME `personal_index.cli:main` group — see the contract
> hole below for where the two packaging files DISAGREE about which symbol to
> call.

## Public surface

Line numbers refer to `personal_index/__main__.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| (module) | 3 | `from personal_index.cli import main` | Imports the click `main` group (defined at `cli.py:55`, `@click.group(invoke_without_command=True)`). |
| (module) | 5-6 | `if __name__ == "__main__": main()` | Runs the `main` group when the package is invoked as `python -m personal_index`. No argument parsing, no exit-code handling, no help printing — it delegates entirely to click. |

## Invariants

- **Thin glue, no logic** (lines 3-6): the module adds no options, no
  subcommands, and no error handling of its own. Every behavior of
  `python -m personal_index` is exactly the behavior of
  `personal_index.cli:main` — the same group the console script and
  `cli.py:1514` invoke.
- **`main` is the single live group** (`cli.py:55`): `main` is a
  `@click.group(cls=click.Group, invoke_without_command=True)` whose callback
  (`cli.py:55-70`) only populates `ctx.obj["data_dir"]` (default
  `".personal_index"`) and `ctx.obj["verbose"]`. Subcommands are registered
  on it at `cli.py:1509-1511` (`dedup`, `health`, `recommend`) plus the
  `@main.command()`-decorated commands defined inline in `cli.py`.
- **No help on bare invocation** (`cli.py:55-70`): because the group uses
  `invoke_without_command=True` but its callback contains NO
  `ctx.get_help()` / `ctx.invoke` / help-echo branch, running
  `python -m personal_index` with no subcommand sets `ctx.obj` and then
  returns silently (exit 0, no output) rather than printing the help text.
  This is a shared property of all three entry paths (they call the same
  `main`), not a `__main__.py`-specific defect.

## Known contract hole

- **The two packaging files disagree on the console-script entry point, and
  `setup.py`'s target does not exist** (see `tickets/ARCH-103.md`):
  `pyproject.toml:23` declares
  `personal-index = "personal_index.cli:main"` (correct — `main` exists at
  `cli.py:55`), but `setup.py:15` declares
  `personal-index=personal_index.cli:cli` — and there is NO `cli` symbol in
  `personal_index/cli.py` (no `def cli`, no `cli =` alias; `grep -rn 'def cli\|cli = main' personal_index/cli.py` returns nothing). A build that
  resolves the entry point from `setup.py` therefore installs a
  `personal-index` command that raises `AttributeError` / fails to load on
  first invocation. The `python -m personal_index` path (`__main__.py`) is
  unaffected (it imports `main` directly), which is why the bug is latent:
  only the `setup.py`-based install is broken.
