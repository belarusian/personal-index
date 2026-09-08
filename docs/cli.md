# CLI (`personal_index.cli`)

Status: **spec** — audited against current code (cycle 174).

The `click` command surface for personal-index: a `main` group, four
subgroups (`interests`, `tags`, `schedule`, `config`), and a set of top-level
commands. Every command resolves its data directory the same way
(`data_dir or ctx.obj.get("data_dir", ".personal_index")`) and builds its
stores through the shared getters below. The page documents the **command
tree**, the **shared helpers** and their return shapes, the **data-dir /
config bootstrap path**, and the **guard paths** — not every option verbatim.

## Bootstrap / data-dir + config path

- **`main` group** (`@click.group(cls=click.Group, invoke_without_command=True)`)
  — options `--data-dir` (default `None`), `--verbose`/`-v` (flag), and a
  `--version` option (`version="0.1.0"`, `prog_name="personal-index"`).
  `main(ctx, data_dir, verbose)` calls `ctx.ensure_object(dict)` and stores
  `ctx.obj["data_dir"] = data_dir or ".personal_index"` and
  `ctx.obj["verbose"] = verbose`. `invoke_without_command=True` means a bare
  `personal-index` (no subcommand) runs `main` and returns after setting
  `ctx.obj` (no default action).
- **`_create_data_dirs(data_dir) -> None`** — `os.makedirs(data_dir,
  exist_ok=True)` then `os.makedirs(<data_dir>/{cache,archive,backups},
  exist_ok=True)`. No return value.
- **`_create_default_config(config_path, data_dir) -> None`** — **guard
  path:** if `config_path` already exists, returns immediately (no write).
  Otherwise writes a YAML dict with keys `data_dir`, `crawler`
  (`max_depth=3`, `max_pages_per_domain=100`, `timeout=30`,
  `politeness_delay=1.0`), `filter` (`min_content_length=100`,
  `min_title_length=3`, `blocked_domains=[]`), and `pipeline`
  (`min_score_threshold=0.0`, `min_content_length=100`) via
  `yaml.dump(..., default_flow_style=False)`.

## Shared store getters

Each returns a fresh store bound to a file under `data_dir`:
- **`get_search_index(data_dir) -> SearchIndex`** — `SearchIndex(db_path=
  <data_dir>/search_index.json)`.
- **`get_tag_store(data_dir) -> TagStore`** — `TagStore(store_path=
  <data_dir>/tags.json)`.
- **`get_interest_store(data_dir) -> InterestStore`** — `InterestStore(
  store_path=<data_dir>/interests.json)` (imported lazily from
  `personal_index.interests`).

## Command tree

    main
    ├── init
    ├── interests (group)
    │   ├── add      -n NAME  -k KW...  -p PRIORITY
    │   ├── list
    │   └── remove   NAME
    ├── tags (group)
    │   ├── add      TAG_NAME URL
    │   ├── list
    │   └── remove   TAG_NAME URL
    ├── import       PATH  -r
    ├── search       QUERY  -n/-l LIMIT  --tag TAG  --format {text,json,csv}  --json
    ├── export       --format {markdown,json,csv}  -o OUTPUT
    ├── status
    ├── crawl        [URL]  -d DEPTH  -m MAX_PAGES
    ├── pipeline     [URLS...]  -i FILE...  -d DEPTH  -m MAX_PAGES  --min-score F
    │                --min-content-length/-l N  --steps/-s STEPS  --no-crawl
    │                --no-filter  --no-score  --no-tag  --no-index  -r
    ├── stats        --format {text,json}
    ├── list         --format {text,json,csv}  -l LIMIT  -s {score,date,title}
    ├── top          --format {text,json}  -l LIMIT
    ├── remove       URL
    ├── clear        --index/--no-index  --tags/--no-tags  --interests/--no-interests
    ├── doctor
    ├── schedule (group)
    │   ├── add      -n NAME  -u URL...  -i INTERVAL  -d DEPTH  -m MAX_PAGES
    │   ├── list
    │   ├── remove   NAME
    │   └── run      NAME
    ├── config (group)
    │   ├── show
    │   ├── set-crawler   -d MAX_DEPTH  -m MAX_PAGES  -t TIMEOUT  -p POLITENESS_DELAY
    │   └── set-schedule  -i INTERVAL  --enabled/--disabled
    ├── verify       --quick
    ├── watch        [PATHS...]  -i INTERVAL  --once
    └── (registered from other modules)
        ├── dedup        (personal_index.cli_dedup.dedup)
        ├── health       (personal_index.cli_health.health)
        └── recommend    (personal_index.cli_recommend.recommend)

`dedup`, `health`, and `recommend` are not defined in this module; they are
imported at the bottom and attached via `main.add_command(...)`.

## Top-level commands (behavior + guard paths)

- **`init`** — resolves `dd`, calls `_create_data_dirs(dd)`, then
  `_create_default_config(config or "config.yaml", dd)`. Echoes the data dir
  and config path. No guard path (idempotent via `exist_ok` / the config
  existence check).
- **`import`** (`import_cmd`) — **guard path:** if `path` does not exist,
  echoes `Error: '<path>' not found` to stderr and `sys.exit(1)`. Otherwise
  builds the three stores, walks `_collect_files(path, recursive)`, and for
  each file calls `_import_single_file` (skipping `None`), then
  `_score_and_tag_page` and `index.add_page`. Echoes the import count.
- **`search`** — **guard path:** if `index.get_page_count() == 0`, echoes a
  "run import/pipeline first" hint and returns (no search). Otherwise
  `index.search(query, limit=limit)`; if `--tag` is set, filters results to
  URLs in `tag_store.get_pages_for_tag(tag)`. Output dispatch: `--json` or
  `--format json` → `_output_search_json`; `--format csv` →
  `_output_search_csv`; else `_output_search_text`.
- **`export`** — **guard path:** if `index.list_pages()` is empty, echoes
  "No indexed content to export." and returns. Otherwise dispatches on
  `--format` (`markdown`/`json`/`csv`; any other value falls back to
  markdown). If `-o OUTPUT` is set, writes to the file; else echoes to
  stdout.
- **`status`** — reads page count, tag count, interests, and
  `_compute_storage_bytes(dd)`; echoes a fixed block. If interests exist,
  calls `_print_interests`; if storage > 0, echoes a formatted size.
- **`crawl`** — **guard path:** if no `url` argument, echoes "Error: URL is
  required" and `sys.exit(1)`. Otherwise builds a crawler via
  `_create_crawler`, runs `crawler.crawl([url])`, prints via
  `_print_crawl_results`, and `crawler.close()` in a `finally`.
- **`pipeline`** — builds a `PipelineRunner` via `_create_pipeline_runner`.
  **Guard path:** if neither `--import-file` nor a `urls` argument is given,
  echoes "No URLs or files specified." and `sys.exit(1)`. Otherwise runs
  `runner.run_from_files(expanded)` (when `--import-file` is set, after
  `_expand_import_files`) or `runner.run(list(urls))`, then
  `_print_pipeline_stats(stats)` + `_print_index_stats(dd)`, with
  `runner.close()` in a `finally`. **Note:** the `--steps` and `--no-*`
  flags are parsed but **not used** in the body (see Contract holes →
  ARCH-13).
- **`stats`** — same data as `status` but with a `--format {text,json}`
  option; JSON emits `indexed_pages`, `interests`, `total_tags`,
  `tagged_pages`, `storage_bytes`.
- **`list`** (`list_pages`) — `pages = _sort_pages(idx.list_pages(),
  sort)[:limit]`. **Guard path:** if empty, echoes `{"pages": []}` (json) or
  a "run pipeline" hint (else) and returns. Dispatches on `--format`
  (`json` → `p.to_dict()` list; `csv` → `_format_pages_csv`; else
  `_format_pages_text`).
- **`top`** — `sorted(idx.list_pages(), key=p.score, reverse=True)[:limit]`;
  JSON emits `{"top_pages": [...]}`, else a numbered text block.
- **`remove`** — iterates `idx.list_pages()`; on the first `p.url == url`,
  calls `idx.remove_page(url)` **and** `get_tag_store(dd).remove_page(url)`
  (drops orphan tag associations), sets `found=True`, breaks. **Guard
  path:** if not found, echoes `Page not found: <url>` and
  `raise SystemExit(1)`. On success echoes the remaining pages as JSON.
- **`clear`** — clears each requested store (`--index` default `True`,
  `--tags` default `True`, `--interests` default `False`). **Guard path:**
  if none of the three flags is set, echoes "Nothing to clear. Use --index,
  --tags, and/or --interests."; else echoes "Done."
- **`doctor`** — runs `_doctor_check_data_dir` (returns `(issues,
  warnings)`), and only when there are no issues, extends warnings with
  `_doctor_check_config`, `_doctor_check_index`, `_doctor_check_interests`.
  Prints via `_doctor_print_results`. **Guard path:** `sys.exit(1)` if any
  issues were found.
- **`verify`** — `os.makedirs(dd, exist_ok=True)`; checks the three stores
  via `_verify_check_store` (each returns `(passed, message)`); unless
  `--quick`, also runs `_verify_check_subdirs` (returns `(passed, failed)`
  counts). Echoes `All checks passed: <p>/<p+f>`.
- **`watch`** — `os.makedirs(dd, exist_ok=True)`; `_validate_watch_paths`
  (**guard path:** exits 1 if no paths, or if any path does not exist).
  **Guard path:** if `--once`, runs `_watch_once(paths, dd)` and returns;
  else echoes "Watch mode started. Press Ctrl+C to stop." and returns
  (no blocking loop in this module).

## Subgroup commands

- **`interests add`** — builds `Interest(name, keywords=list(keywords),
  priority)` and `store.add(interest)`.
- **`interests list`** — **guard path:** if `store.list_all()` is empty,
  echoes "No interests configured." and returns. Else prints each interest
  with enabled/disabled status, priority, and keywords.
- **`interests remove`** — **guard path:** if `store.remove(name)` is
  falsy, echoes "Interest '<name>' not found" and `sys.exit(1)`.
- **`tags add`** — `store.add_tag_to_page(url, tag_name)`.
- **`tags list`** — **guard path:** if `store.list_tags()` is empty, echoes
  "No tags configured." and returns. Else prints each tag with its page
  count.
- **`tags remove`** — **guard path:** if `store.remove_tag_from_page(url,
  tag_name)` is falsy, echoes "Tag '<tag>' not found on <url>" (no exit).
- **`schedule add`** — **guard path:** if a job with the same `name` already
  exists, echoes to stderr and `sys.exit(1)`. Else builds
  `ScheduleConfig(interval_hours, seed_urls, max_pages_per_run,
  crawl_depth)` + `ScheduleEntry(name, config, next_run=now+interval)` and
  `store.add(entry)`.
- **`schedule list`** — **guard path:** if `schedules.json` is absent or
  `store.list_all()` is empty, echoes "No scheduled jobs found." and
  returns. Else prints each job (status, next run, interval, up to 3 URLs).
- **`schedule remove`** — **guard path:** if the store file is absent, or
  `store.remove(name)` is falsy, echoes "not found" and `sys.exit(1)`.
- **`schedule run`** — `_find_schedule_entry` (**guard path:** exits 1 if the
  store file is absent or the job is not found). Runs the job via
  `_create_pipeline_runner` + `runner.run(seed_urls)`; on success persists
  `run_count`, `total_pages_indexed`, `last_run`, `next_run` back to the
  store. **Guard path:** any exception echoes "Job failed: <e>" to stderr and
  `sys.exit(1)`; `runner.close()` in a `finally`.
- **`config show`** — loads `config.yaml` via
  `personal_index.config.loader.load_config` and prints data dir, crawler
  (`max_depth`, `max_pages_per_domain` or `max_pages`, `timeout`,
  `politeness_delay`), and scheduler (`enabled`, `interval_hours`).
- **`config set-crawler`** — loads config (defaulting `config.crawl` to
  `CrawlConfig()` if absent), sets only the non-`None` options, and
  `save_config`.
- **`config set-schedule`** — loads `config.yaml`, sets `interval_hours` /
  `enabled` when provided, and `save_config`.

## Private helpers (contract-relevant)

- **`_score_and_tag_page(page, text, tag_store, interest_store) -> None`** —
  for each interest in `interest_store.matches_any(text, page.url)`, adds the
  interest name as a tag and appends it to `page.matched_interests` (creating
  the list if absent); then sets `page.relevance_score =
  interest_store.total_score(text)`.
- **`_import_single_file(filepath) -> CrawledPage | None`** — reads the file
  (`errors="replace"`); **guard path:** any `OSError` returns `None`, and
  `len(content.strip()) < 10` returns `None`. Else returns
  `CrawledPage(url=f"file://{abspath}", title=basename, content)`.
- **`_collect_files(path, recursive) -> list[str]`** — a file → `[path]`; a
  directory → the `.txt/.md/.html/.htm/.rst` files (recursively when
  `recursive`, else top-level only); anything else → `[]`.
- **`_expand_import_files(import_files, recursive) -> list[str]`** — for each
  path, a directory walked recursively (extensions `.txt/.md/.html/.htm/
  .json/.xml/.rst`) when `recursive`, else the path as-is.
- **`_create_crawler(data_dir, depth, max_pages) -> Crawler`** — builds a
  `Crawler` with `CrawlerConfig(max_depth, max_pages, delay=0.0, timeout=10)`
  and an `InterestStore` bound to `<data_dir>/interests.json`.
- **`_create_pipeline_runner(data_dir, depth, max_pages, min_score,
  min_content_length) -> PipelineRunner`** — builds a `PipelineConfig`
  (`min_score_threshold`, `min_content_length`, `max_pages`, `max_depth`) and
  a `PipelineRunner(data_dir, pipeline_config=config)`.
- **`_print_pipeline_stats(stats) -> None`** — echoes the run stats. Reads
  `stats.pages_filtered_in` (line 632), a valid field on the
  `pipeline_runner.PipelineStats` object the `pipeline` command actually passes
  (the runner returns `pipeline_runner.PipelineStats`, which has
  `pages_filtered_in`; note `models.PipelineStats` is a distinct class with
  `pages_passed_filter`). No `AttributeError` is raised.
- **`_compute_storage_bytes(data_dir) -> int`** — sums `os.path.getsize` over
  every file under `data_dir` (skipping `OSError`); `0` if the dir is absent.
- **`_format_storage_size(total_size) -> str`** — `<1 MiB` → `"<x> KB"`,
  else `"<x> MB"`.
- **`_sort_pages(pages, sort) -> list`** — `date` → by `crawled_at` (desc),
  `title` → by `title.lower()`, else by `score` (desc).
- **`_verify_check_store(name, getter, attr, dd) -> (bool, str)`** — calls
  `getter(dd)` then `getattr(store, attr)()`; returns `(True, msg)` or
  `(False, "<name>: <e>")` on any exception.
- **`_index_file_once(fp, data_dir) -> None`** — reads the file; **guard
  path:** `len(content.strip()) < 10` returns without indexing. Else builds a
  `CrawledPage` and `idx.add_page(page)`.
- **`_watch_once(paths, data_dir) -> None`** — for each path: a file →
  `_collect_files(path, False)`, a directory → `_collect_files(path, True)`,
  else skipped; indexes each file via `_index_file_once`, catching and
  echoing per-file exceptions to stderr.
- **`_validate_watch_paths(paths) -> None`** — **guard path:** exits 1 if
  `paths` is empty or any path does not exist.

## Contract holes

- **Resolved (ARCH-10, cycle 177):** the reported `AttributeError` does not
  exist. `_print_pipeline_stats` reads `stats.pages_filtered_in` (line 632),
  which is a valid field on the `pipeline_runner.PipelineStats` object the
  `pipeline` command actually passes. The ticket conflated it with the distinct
  `models.PipelineStats` class (which has `pages_passed_filter`). No code
  change was needed; the "Bug" note is removed.
- **Dead `_index_file` helper.** `_index_file(fp, data_dir)` (line 1398) is
  defined but **never called** — the live path uses `_index_file_once` (line
  1419). The two differ only in their guard-path style (`_index_file`
  indexes when `len >= 10`; `_index_file_once` returns when `len < 10`). ->
  **ARCH-11**.
- **Resolved (ARCH-12, cycle 177):** the dead module-level `load_config` has been REMOVED. The live config loader is `personal_index.config.loader.load_config`, which the `config` subcommands import and use.
- **`pipeline` `--steps` / `--no-*` flags are parsed but ignored.** The
  `pipeline` command accepts `--steps/-s`, `--no-crawl`, `--no-filter`,
  `--no-score`, `--no-tag`, and `--no-index` (lines 680–686), and the
  function signature binds `steps, no_crawl, no_filter, no_score, no_tag,
  no_index` (lines 690–691), but none of them is referenced in the body —
  the pipeline always runs every stage. A user passing `--no-crawl` or
  `--steps filter,score` gets no effect. -> **ARCH-13**.
