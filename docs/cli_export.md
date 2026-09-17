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
> `export_cmd`, so the command surface of THIS module is untested. The
> contract decision (ARCH-98) is confirmed below: **Option A (wire it)** —
> `export_cmd` is to be registered on the `main` group and `cli.py`'s thinner
> duplicate `export` removed, making the full four-format + three-filter
> surface reachable. The code change is the IMPL lane (the implementer makes
> it when it claims ARCH-98 — not this docs pass).

## Public surface

Line numbers refer to `personal_index/cli_export.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `export_cmd` | 25 | `@click.command("export")` + `--format`/`fmt` (Choice `markdown`/`json`/`csv`/`html`, default `markdown`) + `--output`/`-o` (default `None`) + `--data-dir` (default `None`) + `--tag`/`-t` (multiple) + `--query`/`-q` (default `None`) + `--limit`/`-n` (int, default `0` = all) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, builds `SearchIndex` + `TagStore`, calls `_load_pages(...)`. If no pages, echoes `No pages to export.` and returns. Else `_dispatch_format(...)`, writes to `output` (utf-8) or echoes to stdout. **Confirmed (ARCH-98, Option A):** to be registered on the `main` group (replacing `cli.py`'s thinner duplicate `export`); the code change is the IMPL lane. |

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

## Contract decision (ARCH-98) — CONFIRMED: Option A (wire it)

The dead-public-command-surface hole is **resolved by decision**: **Option A
(wire it)** is confirmed. `export_cmd` (line 25) — the complete, richer
`export` click command (four formats `markdown`/`json`/`csv`/`html` + the
`--tag`/`--query`/`--limit` filters) — is to be **registered on the `main`
group**, and `cli.py`'s thinner duplicate `export` (line 431,
`click.Choice(["markdown", "json", "csv"])`, no filters) plus its private
`_export_markdown`/`_export_json`/`_export_csv` helpers (lines 467-517) are to
be **removed** so there is a single, non-divergent implementation.

**Resulting reachable contract (after the IMPL-lane change):**
`personal-index export` supports `markdown`/`json`/`csv`/`html` +
`--tag`/`--query`/`--limit`, with filter order query → tag → limit (limit
applied last), and an empty result echoing `No pages to export.` and returning
without writing.

**Why Option A over Option B:** the module was clearly written to be the
richer command; `cli.py`'s thinner `export` is the earlier version that was
never removed. Option A gives the user the full surface and deletes the
duplicate divergent implementation (the ticket's "Proposed fix" prefers A).

**Current state (pre-IMPL):** `export_cmd` is still dead code —
`grep -rn 'export_cmd' --include='*.py' personal_index/` returns only its
definition at `cli_export.py:25` (0 production importers), and `cli.py`
registers only `dedup`/`health`/`recommend` (lines 1509-1511). The module's
only test coverage (`tests/test_cli_export_e2e.py`) imports the private
helpers `_load_pages`/`_dispatch_format` directly and never invokes
`export_cmd`.

**IMPL lane (the implementer, when it claims ARCH-98 — NOT this docs pass):**
register `export_cmd` on `main`, delete `cli.py`'s duplicate `export` + its
private `_export_*` helpers, and add a `CliRunner` pinning test that invokes
the REACHABLE `export` end-to-end (default `--limit 0` exports all; `--limit N`
truncates; unsatisfiable `--query`/`--tag` → `No pages to export.`; `--format
html` emits a DOCTYPE + `<table>`). See `tickets/ARCH-98.md`.
