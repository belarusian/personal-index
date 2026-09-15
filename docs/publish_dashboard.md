# `personal_index.publish_dashboard` — spec

Publish the generated docs dashboard + codemap to the `belarusian/search`
GitHub Pages repo. A standalone CLI (has its own `main()` / `__main__`, not a
`cli.py` subcommand) that (1) optionally regenerates the dashboard via
`docs_generator`, (2) validates that the HTML-embedded metadata and the JSON
codemap are in sync, (3) copies the files into the search repo, and (4)
commits + pushes. No crawl, no network fetch of content — it only moves
already-generated artifacts and shells out to `git` / `python -m`.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/publish_dashboard.py` — the *publisher* CLI that ships the
> dashboard. It is **distinct from** `personal_index/docs_generator.py`
> (the *generator* that produces `docs_dashboard.html` +
> `docs_dashboard_metadata.json`, covered by its own page) and from
> `personal_index/cycle_signals.py` (the signal extractor this module shells
> out to, covered by `cycle-signals.md`). `tests/test_publish_dashboard.py:11`
> does `from personal_index import publish_dashboard`;
> `tests/deep/test_publish_dashboard_adversarial.py:22` does
> `from personal_index.publish_dashboard import validate_sync`.

## Public surface

Line numbers refer to `personal_index/publish_dashboard.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `run` | 26 | `(cmd: list[str], cwd: Path \| None = None, check: bool = True) -> subprocess.CompletedProcess` | Runs `cmd` via `subprocess.run(capture_output=True, text=True, cwd=cwd, check=False)`, prints stdout/stderr; if `check` and `returncode != 0`, prints an error and `sys.exit(1)`; otherwise returns the `CompletedProcess` |
| `regenerate` | 40 | `(project_root: Path) -> tuple[Path, Path]` | Runs `python -m personal_index.docs_generator` in `project_root`; returns `(personal_index/docs_dashboard.html, personal_index/docs_dashboard_metadata.json)`; `sys.exit(1)` if the HTML is missing after generation |
| `validate_sync` | 58 | `(html_path: Path, json_path: Path) -> dict` | Compares the JSON codemap `summary` against the HTML-embedded `summary`; returns `{"sync": True, "summary": <json_summary>}` or `{"sync": False, ...}` (see contract below) |
| `_copy_dashboard_files` | 102 | `(html_path, json_path, search_repo: Path, dry_run: bool) -> None` | Copies `index.html` + `codemap.json` into `search_repo` (only when `dry_run` is False); shells out to `cycle_signals` to write `signals.json` (only when `dry_run` is False and the subprocess succeeds) |
| `_git_commit_push` | 144 | `(json_path, search_repo: Path) -> None` | `git add` + `git diff --cached --quiet`; if no staged changes, prints "No changes" and returns; else builds a commit message from the codemap summary and `git commit` + `git push origin HEAD` |
| `publish` | 174 | `(html_path, json_path, search_repo: Path, dry_run: bool = False) -> None` | `sys.exit(1)` if `search_repo` is not a dir; calls `_copy_dashboard_files`; if `dry_run`, prints and returns; else calls `_git_commit_push` |
| `_build_parser` | 191 | `() -> argparse.ArgumentParser` | Flags: `--search-repo` (default `~/Research/search`), `--project-root` (default `Path.cwd()`), `--regenerate`, `--dry-run` |
| `_resolve_dashboard_paths` | 217 | `(project_root: Path, do_regenerate: bool) -> tuple[Path, Path]` | If `do_regenerate`, delegates to `regenerate`; else returns the existing `docs_dashboard.html` / `docs_dashboard_metadata.json`, `sys.exit(1)` if either is missing |
| `main` | 247 | `() -> None` | Parses args, resolves paths, runs `validate_sync`; on `sync: False` warns and (unless `--dry-run`) prompts `input("Publish anyway? [y/N] ")` — aborts unless the answer is `y`; then calls `publish` |

## `validate_sync` contract (the core logic)

Reads the JSON codemap (`json_path`) and the HTML-embedded metadata
(`<script type="application/json" id="codemap-metadata">…</script>` in
`html_path`), HTML-unescapes the embedded payload, and compares the two
`summary` objects.

Guard paths (each returns `{"sync": False, "reason": ...}`):
- codemap JSON is not a dict → `"codemap JSON is not an object"`
- no embedded `<script>` tag found in the HTML → `"no embedded metadata"`
- embedded payload is not a dict → `"embedded metadata is not an object"`

Comparison (lines 87-89):

    for key in json_summary:
        if json_summary[key] != embedded_summary.get(key):
            mismatches.append(...)

**The comparison is one-sided (JSON → HTML).** It iterates only over the keys
of the JSON codemap `summary` and checks each against the HTML-embedded
`summary`. A key that is present **only in the HTML-embedded summary** (absent
from the JSON codemap) is never compared, so `validate_sync` still returns
`{"sync": True}`. The docstring (line 59) reads "Validate that HTML embedded
metadata and JSON codemap are in sync", which reads as *bidirectional*
equality; the actual contract is the weaker one-sided "every JSON-summary key
matches the HTML-embedded summary; HTML-only keys are ignored". See
**Known contract hole** below (ARCH-93).

Success path (line 97) prints a summary line that indexes
`json_summary['total_modules']`, `json_summary['total_errors']`, and
`json_summary['total_warnings']` **directly** (not via `.get`). A summary
missing any of those three keys raises `KeyError` instead of returning a dict.
This is unreachable from the documented entry point (the generator always
writes all three keys), and is pinned as the *current* behavior by
`tests/deep/test_publish_dashboard_adversarial.py::test_missing_display_keys_raises_keyerror`
(documented limitation, not filed).

## Invariants

- The generator (`docs_generator`) writes both the HTML-embedded metadata and
  the JSON codemap from the *same* metadata object, so on the reachable path
  the two summaries are identical and `validate_sync` returns `sync: True`.
- `validate_sync` is pure with respect to the filesystem (it only reads the
  two input files); it never writes.
- The escape round-trip is lossless: a summary value containing HTML special
  characters (`<`, `>`, `&`, `"`, `'`) survives `html.escape` → `html.unescape`
  exactly once (pinned by `test_round_trip_escape_is_lossless`).

## Known contract hole

- **ARCH-93** — `validate_sync`'s "in sync" docstring over-promises
  bidirectional equality; the comparison is one-sided (JSON → HTML only), so
  an HTML-embedded summary with extra keys is still reported as in sync.
  See `tickets/ARCH-93.md`.
