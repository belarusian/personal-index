# `personal_index.cli_top` — spec (RESOLVED: module deleted, Option A)

> **Module identity (dead-implementation disambiguation — RESOLVED):**
> `personal_index/cli_top.py` **has been deleted** (Option A, confirmed by the
> validator at cycle 267 @ main ef8b363; impl328 #1572). It once defined
> `top_pages`, a click command named `"top"` that listed the highest-scored
> indexed pages (via `SearchIndex.list_pages()`, which returns pages sorted by
> `score` descending) and printed them as text or JSON. It was **never imported
> or registered** anywhere in `personal_index/` (grep for `cli_top` across the
> package returns no import), so `top_pages` was unreachable from the
> `personal-index` CLI. The LIVE `top` command — the inline `def top` at
> `personal_index/cli.py:906` (registered on the `main` group via
> `@main.command()` at `cli.py:901`) — is the **sole** implementation, and is
> what `personal-index top` actually runs. The sections below are kept as a
> historical record of what the deleted module was; they are NOT a current
> contract.

## Historical public surface (deleted module)

Line numbers refer to the now-deleted `personal_index/cli_top.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `top_pages` | 19 | `@click.command("top")` + `--limit`/`-l` (default `10`) + `--format`/`fmt` (`click.Choice(["text","json"])`, default `"text"`) + `--data-dir` (default `None`) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, builds `SearchIndex(db_path=<dd>/search_index.json)`, clamps `limit = max(0, limit)`, takes `pages = index.list_pages()[:limit]`. If `pages` is empty, echoes `No indexed pages found. Run 'personal-index pipeline' first.` and returns. Else `_to_json(pages)` (JSON) or `_print_text(pages)` (text). |

### Private helpers

| symbol | line | signature | behavior |
|--------|------|-----------|----------|
| `_to_json` | 37 | `(pages: list) -> dict` | Returns `{"top_pages": [{"rank": i+1, "url": p.url, "title": p.title, "score": p.score, "crawled_at": p.crawled_at, "tags": []} for i, p in enumerate(pages)], "total": len(pages)}`. Note: each entry is a hand-built 6-key dict (NOT `p.to_dict()`), and `tags` is a hardcoded always-empty list. |
| `_print_text` | 48 | `(pages: list) -> None` | Echoes `Top {len(pages)} pages by score:`, a `=` x60 separator, then one numbered block per page: title, `Score: {p.score:.4f}`, `URL:   {p.url}`, `Date:  {p.crawled_at or 'N/A'}`. |

## Historical invariants (deleted module)

- **`list_pages()` is pre-sorted by score descending** (`top_pages`, line 28):
  `SearchIndex.list_pages()` (`personal_index/index.py:154-156`) returns
  `sorted(self._pages.values(), key=lambda p: p.score, reverse=True)`, so the
  `[:limit]` slice yields the top-N by score without an extra sort. (The live
  `cli.py` command re-sorts defensively; this module relied on the
  `list_pages()` contract.)
- **Negative / zero limit clamps to 0** (`top_pages`, line 27):
  `limit = max(0, limit)`, so a negative or zero limit yields an empty slice
  and the "No indexed pages found." hint.
- **Empty index short-circuits** (`top_pages`, lines 29-31): with no pages the
  command echoed the "Run 'personal-index pipeline' first." hint and returned
  before any formatting.

## Contract hole — RESOLVED (Option A: delete the dead parallel implementation)

- **RESOLVED — Option A chosen and executed** (`top_pages` / `_to_json`,
  lines 19-45): `cli_top.py` was never imported or registered on the `main`
  group, so `top_pages` was unreachable from the CLI. Option A (delete the dead
  parallel implementation) was chosen: `personal_index/cli_top.py` and its
  orphaned unit test `tests/test_cli_top.py` were deleted (validator cycle 267
  @ main ef8b363; impl328 #1572). The divergent 6-key JSON contract
  (`rank`, `url`, `title`, `score`, `crawled_at`, `tags: []` + top-level
  `total`) is **gone**. The LIVE `top` command
  (`personal_index/cli.py:906`) is the sole implementation and emits
  `{"top_pages": [p.to_dict() for p in pages]}` only — the full `IndexedPage`
  `to_dict()` (url, title, content, keywords, matched_interests, domain,
  status_code, content_length, language, score, indexed_at, source_interest,
  word_count), with NO `rank`, NO top-level `total`, and NO `tags` key. The
  validator deep test `tests/deep/test_cli_top_adversarial.py` (18 passed,
  incl. `test_json_entries_are_exact_to_dict_no_dead_keys`) is the WITNESS that
  the live contract matches this page. See `tickets/ARCH-100.md`.
