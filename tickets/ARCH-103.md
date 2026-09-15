# ARCH-103 — setup.py console-script entry point targets a non-existent symbol (personal_index.cli:cli)

- **Status:** OPEN
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** setup.py (entry_points) + pyproject.toml ([project.scripts]) + personal_index/__main__.py (the python -m entry point) + personal_index/cli.py (the main group both should target)
- **Issue:** #1505

## Symptom

The package declares its `personal-index` console script in TWO packaging
files, and they point at DIFFERENT symbols:

- `pyproject.toml:23` — `personal-index = "personal_index.cli:main"` (correct:
  `main` is the click group defined at `cli.py:55`).
- `setup.py:15` — `personal-index=personal_index.cli:cli` (BROKEN: there is no
  `cli` symbol in `personal_index/cli.py`).

A build/install that resolves the entry point from `setup.py` therefore
installs a `personal-index` command whose target does not exist. On first
invocation the console script fails to load (setuptools/click raises
`AttributeError: module 'personal_index.cli' has no attribute 'cli'`, or the
entry-point loader reports the missing attribute) — the command is unusable.

The `python -m personal_index` path is UNAFFECTED: `__main__.py:3` imports
`main` directly (`from personal_index.cli import main`) and calls it, so the
module entry point works. That is why the bug is latent — only the
`setup.py`-based install is broken, and the two files silently disagree.

## Evidence (file:line)

- `setup.py:15` — `"personal-index=personal_index.cli:cli"` inside
  `entry_points["console_scripts"]`.
- `pyproject.toml:23` — `personal-index = "personal_index.cli:main"` inside
  `[project.scripts]`.
- `personal_index/cli.py:55` — `def main(ctx, data_dir, verbose):` is the
  `@click.group` (line 50) that both should target.
- `personal_index/cli.py` — NO `cli` symbol: `grep -rn 'def cli\|cli = main\|cli=main' personal_index/cli.py` returns nothing, and there is no `cli =` alias at module scope. The only `__main__` block in cli.py is at line 1514 (`if __name__ == "__main__": main()`), which calls `main`, not `cli`.
- `personal_index/__main__.py:3` — `from personal_index.cli import main` (the
  module entry point targets the correct symbol, confirming `main` is the
  intended live group).

## Classification

This is a genuine, verifiable contract hole (a dead entry-point reference),
not a docstring over-promise: the `setup.py` console script points at a symbol
that does not exist, so a `setup.py`-based install produces a broken
`personal-index` command. It is a one-line packaging fix, but it is CODE
(packaging metadata), so it is an ARCH ticket for the implementer — the
architect does not fix it.

## Proposed fix (single resolution)

1. Change `setup.py:15` from
   `"personal-index=personal_index.cli:cli"` to
   `"personal-index=personal_index.cli:main"`, matching `pyproject.toml:23`.
   (Alternatively, if the project intends to build only from `pyproject.toml`,
   delete the `entry_points` block from `setup.py` so the two files cannot
   diverge again — but the minimal, additive fix is to point it at `main`.)
2. No change to `personal_index/__main__.py` (it already targets `main`
   correctly) or to `personal_index/cli.py`.

## Acceptance criteria

- [ ] `setup.py`'s `console_scripts` entry for `personal-index` targets
      `personal_index.cli:main` (the symbol that exists at `cli.py:55`),
      matching `pyproject.toml:23`.
- [ ] After the fix, `python -c "from personal_index.cli import main"`
      succeeds (the entry-point target resolves) — the symbol the console
      script loads actually exists.
- [ ] `python -m personal_index --help` (via `__main__.py`) still works
      unchanged (the module entry point is not regressed).
- [ ] `docs/__main__.md` Known contract hole section is updated to reflect the
      resolution (moved to a resolved note or removed).
- [ ] `docs/README.md` index entry for `__main__.md` is present (shipped in
      the same PR as this ticket).

## Pinning tests to add (implementer)

- Add ONE test that pins the entry-point target resolves: assert that the
  symbol named in the console-script entry point exists in
  `personal_index.cli`. Concretely, a test that does
  `from personal_index.cli import main` and asserts `main` is the click group
  (e.g. `isinstance(main, click.Group)` or `main.name == "main"`), so a
  regression to a non-existent symbol (like the old `cli`) fails the suite.
  This is the guard-path pin: the normal case is that `main` exists; the
  guard path is that the entry-point string names a symbol that actually
  resolves (the old `cli` would make the import fail).
- No change to the `python -m personal_index` behavior is required; the
  existing module-entry-point path is the witness that `main` is the live
  group.

## Docs update (same PR)

- `docs/__main__.md` — new spec page for `personal_index/__main__.py`
  (purpose, public surface, invariants, the known contract hole).
- `docs/README.md` — add the index entry for `__main__.md`.
