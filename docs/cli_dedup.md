# `personal_index.cli_dedup` — spec

`personal_index/cli_dedup.py` defines `dedup`, a click command named
`"dedup"` that finds (and, unless `--dry-run`, removes) duplicate content
across every indexed page and prints a human-readable report. It is **Wired**:
imported at `personal_index/cli.py:26`
(`from personal_index.cli_dedup import dedup`) and registered on the `main`
group at `personal_index/cli.py:1509` (`main.add_command(dedup)`), so
`personal-index dedup` runs this module (unlike the dead `cli_top`/`cli_export`
parallel implementations).

> **Module identity (live-implementation disambiguation):** this page
> documents `personal_index/cli_dedup.py` — the `dedup` click command and its
> private `_load_indexed_content` / `_build_dedup_items` / `_dispatch_dedup` /
> `_display_result` / `_display_duplicate_groups` / `_remove_duplicates`
> helpers. It is the LIVE `dedup` command (imported + registered on the `main`
> group). It is distinct from the underlying dedup engine it drives,
> `personal_index.content_dedup` (`ContentDeduplicator` / `DedupResult` /
> `DuplicateGroup`), which is a separate module documented by its own spec
> page (`docs/dedup.md`).

## Public surface

Line numbers refer to `personal_index/cli_dedup.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `dedup` | 20 | `@click.command("dedup")` + `--data-dir` (default `None`) + `--method`/`-m` (`click.Choice(["hash","url","similarity","all"])`, default `"all"`) + `--similarity-threshold` (`float`, default `0.9`) + `--dry-run` (`is_flag`) + `@click.pass_context` | Entry point. Resolves `dd = data_dir or ctx.obj.get("data_dir", ".personal_index")`, loads pages via `_load_indexed_content(dd)`. If `pages` is empty, echoes `No indexed content found.` and returns. Else builds items via `_build_dedup_items`, dispatches via `_dispatch_dedup(items, method, similarity_threshold)`, prints via `_display_result` + `_display_duplicate_groups`; if groups exist and not `--dry-run`, removes via `_remove_duplicates`, else echoes `(Dry run - no changes made)`; if no groups, echoes `No duplicates found!`. |

### Private helpers

| symbol | line | signature | behavior |
|--------|------|-----------|----------|
| `_load_indexed_content` | 54 | `(data_dir: str) -> (list, SearchIndex)` | Builds `SearchIndex(db_path=<dd>/search_index.json)`, returns `(idx.list_pages(), idx)`. |
| `_build_dedup_items` | 66 | `(pages) -> list[dict]` | For each page, emits `{"url": page.url, "title": page.title, "content": page.content or ""}`. |
| `_dispatch_dedup` | 82 | `(items, method: str, similarity_threshold: float) -> DedupResult` | Builds `ContentDeduplicator(similarity_threshold=similarity_threshold)` and returns `dedup_by_hash(items)` / `dedup_by_url(items)` / `dedup_by_similarity(items)` / `dedup_all(items)` for `method` `hash` / `url` / `similarity` / else. |
| `_display_result` | 105 | `(result) -> None` | Echoes `result.summary()` then a blank line. |
| `_display_duplicate_groups` | 111 | `(result) -> None` | Echoes `Duplicate Groups:` + a rule, then per group: `Representative: <url>`, `Method: <dedup_method>`, `Threshold: <similarity_score:.2f>`, and one `Duplicate: <url>` line per duplicate. **The `Threshold` line prints `group.similarity_score`** — for similarity groups this is the configured `--similarity-threshold` (the grouping cutoff), not a measured per-group similarity (see the resolved note below). |
| `_remove_duplicates` | 123 | `(idx, result) -> None` | Collects every `group.duplicates` url into a set, calls `idx.remove_page(url)` for each (counting successes), then `idx._save()`; echoes the removed count. |

## Invariants

- **The command is wired and live** (`cli.py:26` + `cli.py:1509`):
  `grep -rn 'cli_dedup' personal_index/ --include=*.py` returns the import
  line, and `main.add_command(dedup)` registers it, so `dedup` is reachable
  from the `personal-index` CLI.
- **Empty-index guard** (`dedup`, line 37-40): when `_load_indexed_content`
  returns an empty `pages` list the command echoes `No indexed content found.`
  and returns before building items or dispatching.
- **`--dry-run` never mutates** (`dedup`, line 47-51): removal via
  `_remove_duplicates` (which calls `idx.remove_page` + `idx._save`) runs only
  when `result.duplicate_groups` is non-empty AND `--dry-run` is absent; with
  `--dry-run` the command echoes `(Dry run - no changes made)` instead.
- **`--method` is a closed choice** (`dedup`, line 13-15): `click.Choice`
  restricts `method` to `hash`/`url`/`similarity`/`all`; any other value is
  rejected by click before the function body runs.
- **`--similarity-threshold` only affects the similarity path**
  (`_dispatch_dedup`, line 82-97): the value is threaded into
  `ContentDeduplicator(similarity_threshold=...)`, but only
  `dedup_by_similarity` / `dedup_all` consult it; `hash` and `url` dedup are
  exact and ignore the threshold.

## Resolved contract note (ARCH-102)

- **`Threshold:` prints the configured cutoff, not a measured similarity** (resolved by `tickets/ARCH-102.md`, Option A — doc/label-only, no behavior change).
  For `method == "similarity"`, `ContentDeduplicator.dedup_by_similarity` sets each
  group's `similarity_score` to `self.similarity_threshold` (`content_dedup.py`), not the
  Jaccard `text_similarity` value that `_find_similarity_group` computes for the grouping
  decision and then discards. To keep the user-facing contract honest, the field
  `DuplicateGroup.similarity_score` now carries a docstring stating its meaning per
  `dedup_method` (1.0 for exact_hash/normalized_url groups; the configured
  `similarity_threshold` for similarity groups), and the CLI's
  `_display_duplicate_groups` (`cli_dedup.py:118`) relabels the line from `Score:` to
  `Threshold:` so the printed number is not misread as a per-group similarity.
  The deep test `test_score_is_threshold`
  (`tests/deep/test_cli_dedup_adversarial.py`) remains the witness: it still pins the
  threshold-as-score behavior and passes unchanged. A CLI-level test
  (`tests/test_cli_dedup.py`) pins the new `Threshold:` label.
