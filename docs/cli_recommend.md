# `personal_index.cli_recommend` — spec

The `recommend` CLI subcommand: a click command (`recommend`) that loads the
indexed pages into a `Recommender`, runs **query-based keyword matching**
(`Recommender.recommend_for_keywords`), and prints the top-N recommendations
with title, URL, score, and reason. It is registered on the `main` group
(`personal_index/cli.py:1511` `main.add_command(recommend)`), so it is a live
`personal-index recommend` entry point.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/cli_recommend.py` — the `recommend` click command and its
> private `_load_recommender` / `_print_recommendations` helpers. It is
> **distinct from** `personal_index/content_recommender.py`, which defines the
> `Recommender` engine with TWO public scoring methods: `recommend(seed, ...)`
> (seed-based, honors all three weights) and `recommend_for_keywords(keywords,
> ...)` (keyword-fraction, `tag_weight` is a no-op). The CLI wires up ONLY
> `recommend_for_keywords`; the seed-based `recommend` is never reachable from
> this command. See the contract hole below.

## Public surface

Line numbers refer to `personal_index/cli_recommend.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `recommend` | 50 | `@click.command("recommend")` + `query` (Argument, `required=False`) + `--top-n`/`-n` (default `5`) + `--data-dir` (default `None`) + `--keyword-weight` (default `0.6`) + `--tag-weight` (default `0.3`) + `--score-weight` (default `0.1`) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, calls `_load_recommender(dd)`. If `item_count == 0`, echoes `No indexed content found. Run 'personal-index pipeline' first.` and returns. Splits `query` into `keywords` (`query.split()` if `query` else `[]`). If ANY of the three weight options was supplied on the command line (`ParameterSource.COMMANDLINE`), calls `recommend_for_keywords(keywords, top_n, keyword_weight, tag_weight, score_weight)`; otherwise calls `recommend_for_keywords(keywords, top_n)` (documented fraction-based defaults). If no recs, echoes `No recommendations found.` and returns. Else `_print_recommendations(recs, top_n)`. |

### Private helpers

| symbol | line | signature | behavior |
|--------|------|-----------|----------|
| `_load_recommender` | 10 | `(data_dir) -> tuple[Recommender, int]` | Builds `SearchIndex(db_path=<dd>/search_index.json)` + `TagStore(store_path=<dd>/tags.json)` + `Recommender(min_score=0.0)`. For each `idx.list_pages()` page, gathers `tag_store.get_tags_for_url(page.url)` tag names and calls `recommender.add_item(ContentItem(url, title, content=page.content or "", keywords=getattr(page, "keywords", []) or [], tags=tag_names, score=page.score))`. Returns `(recommender, recommender.item_count)`. |
| `_print_recommendations` | 32 | `(recs, top_n) -> None` | Echoes `Top {top_n} Recommendations:`, a `=` x50 separator, then one numbered block per rec: title, `URL:`, `Score: {rec.score:.3f}`, `Reason: {rec.reason}`. |

## Invariants

- **Only the keyword path is reachable** (`recommend`, lines 80/87): both the
  explicit-weight and default branches call `recommend_for_keywords`; the
  seed-based `Recommender.recommend(seed, ...)` is never invoked from this
  command, so no CLI input can drive the seed path.
- **Weight options are honored only when explicitly supplied** (`recommend`,
  lines 71-87): `explicit_weights` is `True` only when at least one of
  `--keyword-weight`/`--tag-weight`/`--score-weight` has source
  `ParameterSource.COMMANDLINE`; otherwise the documented fraction-based
  defaults are used (preserving the default CLI output contract).
- **`min_score` is pinned to `0.0`** (`_load_recommender`, line 15): the CLI
  constructs `Recommender(min_score=0.0)`, so no recommendation is dropped by
  the engine's score floor — the only truncation is `top_n`.
- **Empty index short-circuits** (`recommend`, lines 63-65): with
  `item_count == 0` the command echoes the "Run 'personal-index pipeline'
  first." hint and returns before any scoring.

## Known contract hole

- **Docstring over-promises a seed-content path** (`recommend`, line 59): the
  docstring reads "Get content recommendations based on a query **or seed
  content**", but the command exposes only the `query` argument and always
  calls `recommend_for_keywords`; there is no way to pass seed content, so the
  "or seed content" clause is unreachable. The seed-based
  `Recommender.recommend(seed, ...)` exists in the engine but is not wired to
  this command. See `tickets/ARCH-99.md`.
