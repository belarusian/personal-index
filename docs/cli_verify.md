# `personal_index.cli_verify` — spec

The `verify` CLI subcommand: a self-test that exercises the pipeline
components (data-dir writability, interest store, tag store, search index,
content filter, content scorer, and a full mini-pipeline run) against a
scratch data directory, then prints a pass/fail summary and exits non-zero
if any check failed. State is created and cleaned up under `data_dir`; the
full-pipeline self-test writes to a `.verify_pipeline/` subdir that is
removed in a `finally` block.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/cli_verify.py` — the `verify` click command and its
> private `_check_*` / `_run_*` / `_verify_*` helpers. It is **distinct
> from** `personal_index/cli.py` (the `main` click group +
> `interests`/`tags`/`schedule`/`config` subgroups audited in
> `cli.md`) and from the `pipeline` / `pipeline-orchestrator` /
> `pipeline-e2e` modules (which *run* the pipeline; this module only
> *checks* that the components work). `tests/test_cli_verify.py:9` does
> `from personal_index.cli_verify import verify`; the deep test
> `tests/deep/test_content_filter_adversarial.py:476`
> (`test_cli_verify_runs`) invokes the `verify` command end-to-end and is
> the witness for the command surface.

## Public surface

Line numbers refer to `personal_index/cli_verify.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `verify` | 382 | `@click.command("verify")` + `--data-dir` (default `None`) + `--quick`/`-q` (flag) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, `os.makedirs(dd, exist_ok=True)`, runs `_run_checks(dd, quick)`, then `_cleanup_verify_files(dd)`, then `_build_summary(...)`. |
| `_run_checks` | 327 | `(data_dir: str, quick: bool) -> tuple[int, int, list[str]]` | Runs the 6 `_VERIFY_CHECKS` (always) + the full-pipeline self-test (unless `quick`). Returns `(checks_passed, checks_total, errors)`. |
| `_build_summary` | 296 | `(checks_passed: int, checks_total: int, errors: list[str]) -> None` | Prints `Results: <passed>/<total> checks passed`; if `errors` non-empty prints each and `sys.exit(1)`; else prints the all-passed line. |
| `_cleanup_verify_files` | 366 | `(data_dir: str) -> None` | Removes `verify_interests.json` / `verify_tags.json` / `verify_index.json` if present. |
| `_VERIFY_CHECKS` | 317 | `list[tuple[str, Callable[[str], tuple[bool, str]]]]` | 6 `(name, check_fn)` pairs: data-dir, interest store, tag store, search index, content filter, content scorer. |

### Private check helpers (all return `tuple[bool, str]`)

| symbol | line | behavior |
|--------|------|----------|
| `_check_data_dir` | 18 | Writes + removes `.verify_test` in `data_dir`; `(True, "")` on success, `(False, str(e))` on `OSError`. |
| `_check_interest_store` | 34 | Adds a `verify_test` interest to `verify_interests.json`, lists it, clears + saves; `(True, "")` iff `len(interests) > 0`. |
| `_check_tag_store` | 53 | Tags `http://test.com` with `verify` in `verify_tags.json`, reads it back, clears + saves; `(True, "")` iff the tag round-trips. |
| `_check_search_index` | 72 | Adds a `CrawledPage` to `verify_index.json`, searches `verification`, removes the page + saves; `(True, "")` iff `len(results) > 0`. |
| `_check_content_filter` | 96 | Builds `ContentFilter(FilterConfig(min_content_length=10))`; `(True, "")` iff `should_include` on a 38-char page is `True`. |
| `_check_content_scorer` | 117 | Builds `ContentScorer(ScoreWeights())`; `(True, "")` iff `score(...).total > 0`. |

### Full-pipeline self-test helpers

| symbol | line | signature | behavior |
|--------|------|-----------|----------|
| `_check_full_pipeline` | 262 | `(data_dir: str) -> tuple[bool, str]` | Creates test content, sets up a mini pipeline, creates a test page, runs filter -> score -> tag-index; `(True, "")` on success, `(False, <reason>)` on any stage failure or `RuntimeError`/`OSError`/`ValueError`. `finally` removes the `.verify_pipeline/` subdir. |
| `_create_test_content` | 138 | `(data_dir: str) -> tuple[str, str]` | Writes a ~40-word Python article to `.verify_pipeline/test_article.txt`; returns `(test_data_dir, test_file_path)`. |
| `_setup_mini_pipeline` | 161 | `(test_data_dir: str) -> dict` | Builds `InterestStore` (python interest), `TagStore`, `SearchIndex`, `ContentFilter` (wired to the interest store), `ContentScorer`; returns them keyed `interest_store`/`tag_store`/`search_index`/`filter`/`scorer`. |
| `_create_test_page` | 190 | `(data_dir: str) -> CrawledPage` | Reads `test_article.txt`; returns a `CrawledPage(url=<file path>, title="Python Overview", content=<text>)`. |
| `_run_score` | 224 | `(scorer, page, content) -> float` | Scores with `keyword_matches=2, total_keywords=2, word_count=len(content.split()), domain_authority=0.5`; sets `page.relevance_score` and returns `score.total`. |
| `_run_tag_index` | 245 | `(tag_store, search_index, page) -> list` | Tags the page `python` + `programming`, `add_page`, returns `search_index.search("python")`. |
| `_verify_filter` | 291 | `(filter, page) -> bool` | Returns `filter.should_include(page)`. **This is the filter check the full pipeline actually calls** (line 277). |

## Invariants

- **Check count** (`_run_checks`, lines 341-358): `checks_total` is 6 for
  `--quick` (the `_VERIFY_CHECKS` loop) and 7 otherwise (the loop + the
  full-pipeline self-test at line 354). `checks_passed` increments only on
  a `True` return; every `False` appends `✗ <name>: <msg>` to `errors`.
- **Exit code** (`_build_summary`, lines 305-312): the command exits `1`
  iff `errors` is non-empty, else `0`. A partial pass (e.g. 6/7) is a
  failure.
- **Cleanup is best-effort** (`_cleanup_verify_files`, lines 366-373): only
  the three top-level `verify_*.json` files are removed; the
  `.verify_pipeline/` subdir is removed by `_check_full_pipeline`'s
  `finally` (line 289, `shutil.rmtree(..., ignore_errors=True)`), so it is
  cleaned even on a stage exception.
- **Filter check in the full pipeline** (line 277): `_check_full_pipeline`
  calls `_verify_filter` (returns `bool`), the surviving filter check.

## Resolved contract holes

- **`_run_filter` dead code / duplicate filter check — RESOLVED (ARCH-97,
  VERIFIED):** Option A was chosen (cycle 261 / #1564@dcf0461) — the dead
  `_run_filter` helper (line 209, `tuple[bool, str]`) was deleted from
  `personal_index/cli_verify.py`. The full pipeline's filter stage now calls
  the surviving `bool`-returning `_verify_filter` (line 291) at line 277, so
  the duplicate `tuple[bool, str]` check is gone. Witness: the pinning deep
  test `tests/deep/test_pipeline_filter_adversarial.py` (12 passed, incl.
  end-to-end CLI) + `tests/test_cli_verify.py` (12 passed). See
  `tickets/ARCH-97.md`.
