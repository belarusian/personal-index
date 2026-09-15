# `personal_index.cli_export` — spec

The `export` CLI subcommand **as designed in this module**: a click command
(`export_cmd`) that exports indexed pages in four formats (markdown, JSON,
CSV, HTML), with optional filtering by search query, by tag, and by a page
limit. It loads pages from the `SearchIndex`, applies the query/tag/limit
filters, dispatches to a per-format exporter, and writes the result to a file
or stdout.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/cli_export.py` — the standalone `export_cmd` click command
> and its private `_load_pages` / `_dispatch_format` / `_export_*` helpers.
> It is **distinct from** `personal_index/cli.py`, which defines its OWN
> separate `export` command (line 431, `@main.command()`) that is the one
> actually registered on the `main` group. `cli.py`'s `export` is thinner:
> it supports only `markdown`/`json`/`csv` (no `html`) and has NO
> `--tag`/`--query`/`--limit` options. `tests/test_cli_export_e2e.py` imports
> only the private helpers `_load_pages` (lines 95/119/148/160) and
> `_dispatch_format` (lines 193/218/244/269) — it never imports or invokes
> `export_cmd`, so the command surface of THIS module is untested. See the
> contract hole below.

## Public surface

Line numbers refer to `personal_index/cli_export.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `export_cmd` | 25 | `@click.command("export")` + `--format`/`fmt` (Choice `markdown`/`json`/`csv`/`html`, default `markdown`) + `--output`/`-o` (default `None`) + `--data-dir` (default `None`) + `--tag`/`-t` (multiple) + `--query`/`-q` (default `None`) + `--limit`/`-n` (int, default `0` = all) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, builds `SearchIndex` + `TagStore`, calls `_load_pages(...)`. If no pages, echoes `No pages to export.` and returns. Else `_dispatch_format(...)`, writes to `output` (utf-8) or echoes to stdout. **Never registered on the `main` group** — see contract hole. |

### Private helpers

| symbol | line | signature | behavior |
|--------|------|-----------|----------|
| `_load_pages` | 57 | `(index, tag_store, query, tag, limit) -> list` | `pages = index.list_pages()`. If `query`: `index.search(query, limit=max(len(pages), 1000))`, keep pages whose `url` is in the result set. If `tag`: keep pages whose `tag_store.get_tags_for_page(url)` intersects `set(tag)`. If `limit > 0`: `pages = pages[:limit]`. Returns the filtered list. |
| `_dispatch_format` | 95 | `(fmt, pages, tag_store) -> str` | Maps `markdown`/`json`/`csv`/`html` to `_export_markdown`/`_export_json`/`_export_csv`/`_export_html`; `dispatch.get(fmt, _export_markdown)` so an unknown `fmt` falls back to markdown. |
| `_tag_names` | 116 | `(tags) -> list[str]` | Maps each tag to `t.name` if it has a `name` attr else `str(t)`. |
| `_export_markdown` | 127 | `(pages, tag_store) -> str` | Header (`# Personal Index Export`, UTC timestamp, total) + one `## <title>` block per page with URL, score (`page.score` or `page.relevance_score`), tags, and a 300-char content snippet. |
| `_export_json` | 153 | `(pages, tag_store) -> str` | `json.dumps` of a list of `{url, title, score, content_length, tags, crawled_at}` dicts, `indent=2, default=str`. |
| `_export_csv` | 171 | `(pages, tag_store) -> str` | Header `url,title,score,tags,content_length` + one quoted row per page (title `"`-escaped, tags `;`-joined). |
| `_export_html` | 185 | `(pages, tag_store) -> str` | Full HTML document with a styled `<table>` (Title/URL/Score/Tags); title `<`/`>` escaped to `&lt;`/`&gt;`. |

## Invariants

- **Format dispatch is total over the declared choices** (`_dispatch_format`,
  lines 107-112): all four `click.Choice` values map to a real exporter, and
  the `.get(fmt, _export_markdown)` default means even an out-of-choice `fmt`
  (only reachable by calling `_dispatch_format` directly, since click
  validates the choice) degrades to markdown rather than raising.
- **Filter order is query → tag → limit** (`_load_pages`, lines 74-90): the
  query filter runs first (narrowing to search hits), then the tag filter,
  then the limit slice. The limit is applied LAST, so `--limit` bounds the
  final (already query+tag-filtered) set.
- **Query filter is a set-intersection, not a re-rank** (`_load_pages`,
  lines 76-79): it calls `index.search(query, limit=max(len(pages), 1000))`
  and keeps the pages whose URL appears in the result set, preserving the
  original `list_pages()` order rather than the search ranking.
- **Empty result short-circuits** (`export_cmd`, lines 43-45): with no pages
  after filtering the command echoes `No pages to export.` and returns
  without writing a file or dispatching a format.

## Known contract holes

- **`export_cmd` is dead code — it is never registered on the `main` group**
  (ARCH-98): `export_cmd` (line 25) is a complete, richer `export` click
  command (adds the `html` format and `--tag`/`--query`/`--limit` filters),
  but **nothing imports it**. `personal_index/cli.py` registers only
  `dedup`/`health`/`recommend` via `main.add_command(...)` (lines 1509-1511)
  and defines its OWN separate `export` command (line 431, `@main.command()`)
  that is the one actually reachable as `personal-index export`. That
  registered `export` is thinner: `click.Choice(["markdown", "json", "csv"])`
  (no `html`) and no `--tag`/`--query`/`--limit` options. So the entire
  `export_cmd` surface — the `html` format and all three filters — is
  unreachable from the CLI. The module's only test coverage
  (`tests/test_cli_export_e2e.py`) imports the private helpers
  `_load_pages`/`_dispatch_format` directly and never invokes `export_cmd`,
  so the dead command is never exercised end-to-end. See
  `tickets/ARCH-98.md`.
