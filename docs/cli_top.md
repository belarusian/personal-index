# `personal_index.cli_top` — spec

`personal_index/cli_top.py` defines `top_pages`, a click command named
`"top"` that lists the highest-scored indexed pages (via
`SearchIndex.list_pages()`, which returns pages sorted by `score`
descending) and prints them as text or JSON.

> **Module identity (dead-implementation disambiguation):** this page
> documents `personal_index/cli_top.py` — the `top_pages` click command and
> its private `_to_json` / `_print_text` helpers. It is **distinct from** the
> LIVE `top` command, which is the inline `def top` at
> `personal_index/cli.py:906` (registered on the `main` group via
> `@main.command()` at `cli.py:901`). `cli_top.py` is **never imported or
> registered** anywhere in `personal_index/` (grep for `cli_top` across the
> package returns no import), so `top_pages` is unreachable from the
> `personal-index` CLI. The live command is what `personal-index top`
> actually runs. See the contract hole below.

## Public surface

Line numbers refer to `personal_index/cli_top.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `top_pages` | 19 | `@click.command("top")` + `--limit`/`-l` (default `10`) + `--format`/`fmt` (`click.Choice(["text","json"])`, default `"text"`) + `--data-dir` (default `None`) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, builds `SearchIndex(db_path=<dd>/search_index.json)`, clamps `limit = max(0, limit)`, takes `pages = index.list_pages()[:limit]`. If `pages` is empty, echoes `No indexed pages found. Run 'personal-index pipeline' first.` and returns. Else `_to_json(pages)` (JSON) or `_print_text(pages)` (text). |

### Private helpers

| symbol | line | signature | behavior |
|--------|------|-----------|----------|
| `_to_json` | 37 | `(pages: list) -> dict` | Returns `{"top_pages": [{"rank": i+1, "url": p.url, "title": p.title, "score": p.score, "crawled_at": p.crawled_at, "tags": []} for i, p in enumerate(pages)], "total": len(pages)}`. Note: each entry is a hand-built 6-key dict (NOT `p.to_dict()`), and `tags` is a hardcoded always-empty list. |
| `_print_text` | 48 | `(pages: list) -> None` | Echoes `Top {len(pages)} pages by score:`, a `=` x60 separator, then one numbered block per page: title, `Score: {p.score:.4f}`, `URL:   {p.url}`, `Date:  {p.crawled_at or 'N/A'}`. |

## Invariants

- **`list_pages()` is pre-sorted by score descending** (`top_pages`, line 28):
  `SearchIndex.list_pages()` (`personal_index/index.py:154-156`) returns
  `sorted(self._pages.values(), key=lambda p: p.score, reverse=True)`, so the
  `[:limit]` slice yields the top-N by score without an extra sort. (The live
  `cli.py` command re-sorts defensively; this module relies on the
  `list_pages()` contract.)
- **Negative / zero limit clamps to 0** (`top_pages`, line 27):
  `limit = max(0, limit)`, so a negative or zero limit yields an empty slice
  and the "No indexed pages found." hint.
- **Empty index short-circuits** (`top_pages`, lines 29-31): with no pages the
  command echoes the "Run 'personal-index pipeline' first." hint and returns
  before any formatting.

## Known contract hole

- **Dead parallel implementation with a divergent JSON contract**
  (`top_pages` / `_to_json`, lines 19-45): `cli_top.py` is never imported or
  registered on the `main` group, so `top_pages` is unreachable from the CLI.
  The LIVE `top` command (`personal_index/cli.py:906`) emits
  `{"top_pages": [p.to_dict() for p in pages]}` — the full `IndexedPage`
  `to_dict()` (url, title, content, keywords, matched_interests, domain,
  status_code, content_length, language, score, indexed_at, source_interest,
  word_count), with NO `rank`, NO top-level `total`, and NO `tags` key. The
  dead `cli_top.py` `_to_json` instead emits a hand-built 6-key entry
  (`rank`, `url`, `title`, `score`, `crawled_at`, `tags`) plus a top-level
  `total`, where `tags` is a hardcoded always-empty list even though
  `IndexedPage` has **no `tags` field** (its per-page data is `keywords` and
  `matched_interests`, both dropped here). The two implementations therefore
  expose two incompatible JSON contracts for the same `top` command name: the
  unit test `tests/test_cli_top.py` pins the dead contract (`rank`, `total`,
  `tags`), while the validator deep test
  `tests/deep/test_cli_top_adversarial.py` pins the LIVE contract
  (`top_pages` only, `to_dict()` entries). See `tickets/ARCH-100.md`.
