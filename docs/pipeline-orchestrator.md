# Pipeline Orchestrator (`personal_index.pipeline_orchestrator`)

Status: **spec** — audited against current code (cycle 173).

End-to-end pipeline that ties the components together:
**crawl → filter → score → tag → index** (search is a separate method).
`PipelineOrchestrator` owns one instance of each component and coordinates
data flow between stages, accumulating `PipelineStats` as it goes.

## PipelineResult (dataclass)
Fields (all defaulted):
- `stats: PipelineStats` (default `PipelineStats()`).
- `pages: list[CrawledPage]` (default `[]`) — the pages that reached the
  index stage (extended by `_run_index_stage`).
- `errors: list[str]` (default `[]`) — `str(e)` of any caught pipeline error.
- `success: bool` (default `True`) — set `False` when a stage raises.
- `summary() -> str` — a human-readable multi-line block: a header, then one
  line each for `pages_crawled`, `pages_extracted`, `pages_passed_filter`,
  `pages_scored`, `pages_tagged`, `pages_indexed`, `tags_applied`,
  `len(errors)`, and `elapsed_seconds` (1 decimal). Returns the lines joined
  by `"\n"`.

## PipelineOrchestrator
`PipelineOrchestrator(data_dir: str = ".personal_index",
config: PipelineConfig | None = None,
progress_callback: Any = None)`.
- Stores `self.data_dir`, `self.config` (`config or PipelineConfig()`), and
  `self.progress_callback`.
- Constructor side effects (in order): `_ensure_dirs`, `_init_stores`,
  `_init_processors`, `_init_crawler`.
- **`_ensure_dirs(data_dir)`** — `os.makedirs(data_dir, exist_ok=True)` plus
  `cache/`, `archive/`, `backups/` subdirs (all `exist_ok=True`).
- **`_init_stores(data_dir)`** — builds `self.interest_store`
  (`interests.json`), `self.tag_store` (`tags.json`), and `self.search_index`
  (`search_index.json`) under `data_dir`.
- **`_init_processors()`** — builds `self.content_extractor`
  (`ContentExtractor()`), `self.content_scorer`
  (`ContentScorer(weights=ScoreWeights())`), and `self.content_filter`
  (`ContentFilter(config=FilterConfig(min_content_length=
  self.config.min_content_length, require_interest_match=False),
  interest_store=self.interest_store)`).
- **`_init_crawler()`** — builds `self.crawler`
  (`Crawler(config=CrawlerConfig(max_depth=self.config.max_depth,
  max_pages=self.config.max_pages, timeout=30, delay=1.0),
  interest_store=self.interest_store)`).

### Public entry points
- **`run(seed_urls: list[str]) -> PipelineResult`** — the crawl path.
  - Stage 1: `self.crawler.crawl(seed_urls)`; sets `stats.pages_crawled`.
  - Then `_execute_stages(crawled_pages, result, start_time)`.
  - **Guard path:** any `RuntimeError`/`OSError` is caught — logged,
    `str(e)` appended to `result.errors`, `result.success = False`,
    `stats.elapsed_seconds` set, and the (partial) `result` is returned.
    No other exception type is caught.
- **`run_from_files(filepaths: list[str]) -> PipelineResult`** — the local-file
  path (skips crawl).
  - Stage 1: `_stage_read(filepaths)`; sets `stats.pages_crawled` to the
    number of files successfully read.
  - Then `_execute_stages(pages, result, start_time)`.
  - **Guard path:** identical to `run` (catches `RuntimeError`/`OSError`).
- **`search(query: str, limit: int = 20) -> list[Any]`** — delegates to
  `self.search_index.search(query, limit=limit)`; returns its result list
  unchanged.
- **`close() -> None`** — `self.crawler.close()`, `self.search_index.close()`,
  then `self.tag_store._save()` and `self.interest_store._save()`.

### Shared stage runner
- **`_execute_stages(pages, result, start_time) -> PipelineResult`** — sets
  `stats.pages_extracted = len(pages)`, then runs the four stages in order
  `_run_filter_stage` → `_run_score_stage` → `_run_tag_stage` →
  `_run_index_stage`, each consuming the previous stage's output, then sets
  `stats.elapsed_seconds` and returns `result`.
- **`_run_stage(items, stage_fn, stage_name) -> list[CrawledPage]`** — the
  generic loop: emits progress `(stage_name, 0, total)`, then for each page
  calls `stage_fn(page)` (a `Callable(page) -> bool`); keeps the page in the
  output only when `stage_fn` returns `True`; emits progress
  `(stage_name, i+1, total)` after each page. Returns the kept list.
- **`_emit_progress(stage, current, total) -> None`** — calls
  `self.progress_callback(stage, current, total)` only when a callback is
  set; swallows `RuntimeError`/`TypeError` from the callback (no re-raise).

### Per-stage runners (the LIVE path)
- **`_run_filter_stage(pages, result)`** — `_run_stage` with `_apply_filter`;
  sets `stats.pages_passed_filter = len(out)` and
  `stats.pages_filtered_out = len(pages) - len(out)`.
- **`_run_score_stage(pages, result)`** — `_run_stage` with `_apply_score`;
  sets `stats.pages_scored = len(out)`.
- **`_run_tag_stage(pages, result)`** — `_run_stage` with `_apply_tag`; sets
  `stats.pages_tagged = len(out)`.
- **`_run_index_stage(pages, result)`** — `_run_stage` with `_apply_index`;
  sets `stats.pages_indexed = len(out)` and `result.pages.extend(out)`.

### Per-page callbacks (the LIVE path)
- **`_apply_filter(page, result) -> bool`** — returns
  `self.content_filter.should_include(page)`.
- **`_apply_score(page) -> bool`** — sets `page.relevance_score =
  self._score_page(page)`; always returns `True` (score never drops a page).
- **`_apply_tag(page, result) -> bool`** — `tags = self._tag_page(page)`;
  increments `stats.pages_tagged += 1` and `stats.tags_applied += len(tags)`;
  always returns `True`.
- **`_apply_index(page, result) -> bool`** — `self.search_index.add_page(page)`;
  increments `stats.pages_indexed += 1`; always returns `True`.

### Private helpers (contract-relevant)
- **`_score_page(page) -> float`** — counts keyword matches of every interest
  keyword against the lower-cased page content, populating
  `page.matched_interests` (deduped, first-appearance order). **Guard path:**
  when there are zero configured interest keywords (`total_keywords == 0`),
  returns the neutral `0.5`. Otherwise calls
  `self.content_scorer.score(keyword_matches, total_keywords, word_count,
  domain_authority=0.5)` and returns `score_result.total` (or `0.0` when the
  result has no `total` attribute).
- **`_tag_page(page) -> list[str]`** — builds `text = f"{page.title}
  {page.content}"`; adds one tag per interest from
  `self.interest_store.matches_any(text, page.url)`, then up to 5 keyword tags
  from `extract_keywords(page.content or "", max_keywords=5)`; each is written
  via `self.tag_store.add_tag_to_page(page.url, tag)`. Returns the tag list.
- **`_read_file_as_page(filepath) -> CrawledPage | None`** — reads the file
  (`encoding="utf-8", errors="replace"`); title = `os.path.basename`, or the
  first `# ` markdown heading when content starts with `"# "`. Returns a
  `CrawledPage(url=f"file://{abspath}", title, content, word_count)`.
  **Guard path:** any `OSError`/`ValueError` returns `None` (the file is
  skipped, not fatal).
- **`_stage_read(filepaths) -> list[CrawledPage]`** — maps
  `_read_file_as_page` over `filepaths`, keeping only non-`None` results.
  This is the ONLY live `_stage_*` method (used by `run_from_files`).

## Contract holes
- **Double-written stats counters.** `stats.pages_tagged` and
  `stats.pages_indexed` are written twice per run: incremented per-page inside
  `_apply_tag`/`_apply_index`, then **overwritten** by `len(out)` in
  `_run_tag_stage`/`_run_index_stage`. The final value equals the per-page
  count only because every `_apply_*` callback returns `True` (so `len(out)`
  equals the number of increments). This is a latent invariant: if a callback
  ever returned `False`, the two write sites would silently disagree. ->
  **ARCH-9**.
