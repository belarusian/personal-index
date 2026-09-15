# `personal_index.cli_health` — spec

`personal_index/cli_health.py` defines `health`, a click command named
`"health"` that runs a content-health audit over every indexed page and prints
a human-readable report. It is **Wired**: imported at
`personal_index/cli.py:27` (`from personal_index.cli_health import health`)
and registered on the `main` group, so `personal-index health` runs this
module (unlike the dead `cli_top`/`cli_export` parallel implementations).

> **Module identity (live-implementation disambiguation):** this page
> documents `personal_index/cli_health.py` — the `health` click command and
> its private `_load_stores` / `_build_health_items` / `_build_config` /
> `_print_report` / `_print_issues` / `_severity_icon` helpers. It is the LIVE
> `health` command (imported + registered on the `main` group). It is distinct
> from the underlying checker it drives, `personal_index.content_health`
> (`ContentHealthChecker` / `ContentHealthCheck`), which is a separate module
> documented by its own spec page.

## Public surface

Line numbers refer to `personal_index/cli_health.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `health` | 20 | `@click.command("health")` + `--data-dir` (default `None`) + `--min-content-length` (`int`, default `50`) + `--min-title-length` (`int`, default `3`) + `--require-tags` (`is_flag`) + `--min-score` (`float`, default `0.0`) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, loads stores via `_load_stores(dd)`, takes `pages = idx.list_pages()`. If `pages` is empty, echoes `No indexed content found. Run 'personal-index pipeline' first.` and returns. Else builds items via `_build_health_items`, a config via `_build_config`, runs `ContentHealthChecker(config=config).check_all(items)`, and prints via `_print_report`. |

### Private helpers

| symbol | line | signature | behavior |
|--------|------|-----------|----------|
| `_load_stores` | 39 | `(data_dir: str) -> (SearchIndex, TagStore)` | Builds `SearchIndex(db_path=<dd>/search_index.json)` and `TagStore(store_path=<dd>/tags.json)` and returns both. |
| `_build_health_items` | 47 | `(pages, tag_store) -> list[dict]` | For each page, emits `{"url", "title" (or ""), "content" (or ""), "tags" (from `tag_store.get_tags_for_url`), "score", "status_code" (via `getattr(page, "status_code", 200)")}`. |
| `_build_config` | 61 | `(min_content_length, min_title_length, require_tags, min_score) -> ContentHealthCheck` | Returns `ContentHealthCheck(min_content_length=..., min_title_length=..., require_tags=..., require_score=min_score > 0, min_score=...)`. **Does NOT set `max_title_length` or `min_tags`** — both fall back to the dataclass defaults (200 and 1). See the contract hole below. |
| `_print_report` | 71 | `(report) -> None` | Echoes `report.summary()`, a blank line, then `Issues Found (N):` + `_print_issues` if `report.total_issues > 0`, else `✓ All content is healthy!`. |
| `_print_issues` | 80 | `(report) -> None` | For each result with issues, echoes the url then one line per issue: `{icon} [{severity}] {message}` and, if present, `→ {suggestion}`. |
| `_severity_icon` | 91 | `(severity: str) -> str` | Maps `critical`→🔴, `high`→🟠, `medium`→🟡, `low`→🔵, else ⚪. |

## Invariants

- **The command is wired and live** (`cli.py:27`): `grep -rn 'cli_health'
  personal_index/ --include=*.py` returns the import line, so `health` is
  reachable from the `personal-index` CLI.
- **Empty-index guard** (`health`, line 24-26): when `idx.list_pages()` is
  empty the command echoes the "No indexed content found" message and returns
  before building any items or running the checker.
- **`require_score` is derived, not a flag** (`_build_config`, line 66): the
  CLI has no `--require-score` option; the score check runs only when
  `--min-score > 0` (`require_score=min_score > 0`). A `--min-score 0.0`
  (the default) therefore disables the score check entirely.
- **`status_code` defaults to 200** (`_build_health_items`, line 57): pages
  without a `status_code` attribute are treated as HTTP 200 (healthy) via
  `getattr(page, "status_code", 200)`.

## Known contract hole

- **Two of the seven checker knobs are unreachable from the CLI** (see
  `tickets/ARCH-101.md`): `ContentHealthCheck` has seven fields
  (`min_content_length`, `min_title_length`, `max_title_length`,
  `require_tags`, `min_tags`, `require_score`, `min_score`), but the `health`
  command exposes only five options and `_build_config` never sets
  `max_title_length` (default 200, gates the `title_too_long` check) or
  `min_tags` (default 1, gates the `missing_tags` check). A user cannot tune
  two of the seven checks from the CLI.
