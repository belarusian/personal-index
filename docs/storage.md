# storage — Exact Contract

Module: `personal_index/storage.py` (174 lines)

File-based persistence layer for the three core record types: `Interest`,
`CrawlConfig`, and `IndexedPage` (all from `personal_index.models`). One
public type, `Storage`, backed by three JSON files in a single `data_dir`.
There is no locking; `Storage` is single-threaded by contract.

## Public API

### Storage

`__init__(self, data_dir: str = ".personal-index")` — sets `self.data_dir =
Path(data_dir)` and creates it (`mkdir(parents=True, exist_ok=True)`).
Fixes the three backing files: `interests.json`, `config.json`,
`pages.json` (all under `data_dir`), then calls `_ensure_files()`.

Private helpers (not part of the public contract, but they define the
persistence behavior):

- `_ensure_files()` — for each of the three files, if it does not exist it is
  written with an empty seed: `interests.json` -> `"[]"`, `config.json` ->
  `"{}"`, `pages.json` -> `"[]"`. Existing files are left untouched.
- `_read_json(filepath: Path) -> list | dict` — the default return value is
  `[]` when `filepath.name` is `interests.json` or `pages.json`, else `{}`.
  Reads the file text; if it is empty/whitespace it returns the default.
  Otherwise `json.loads`; on `json.JSONDecodeError` it **silently returns the
  default** (no error, no log, no backup).
- `_write_json(filepath: Path, data)` — `filepath.write_text(json.dumps(data,
  indent=2, default=str))`. Writes **directly to the target file** — no
  temp-file-and-rename, no fsync, no backup of the previous contents.

Interests:

- `add_interest(interest: Interest) -> Interest` — upsert keyed by
  `interest.name`. On a name collision the existing entry is replaced in place
  by `interest.to_dict()`; otherwise it is appended. Returns the passed
  `interest` (unmutated).
- `get_interests() -> list[Interest]` — all interests as `Interest` objects
  (via `Interest.from_dict`); returns `[]` if the file is not a list.
- `get_interest(name: str) -> Interest | None` — first interest with
  `name == name`, else `None`.
- `remove_interest(name: str) -> bool` — drops every entry whose `name`
  matches; returns `True` if at least one was removed, `False` otherwise.
- `list_interests() -> list[dict]` — summary dicts with exactly the keys
  `name`, `keywords`, `url_patterns`, `topics`, `enabled`, `created_at`
  (note: `priority`, `interest_type`, `value`, `topic`, `match_mode` are
  omitted).

Crawl config:

- `save_config(config: CrawlConfig) -> CrawlConfig` — writes
  `config.to_dict()` to `config.json`; returns `config`.
- `get_config() -> CrawlConfig` — `CrawlConfig()` (all defaults) when the file
  is empty or not a dict; otherwise `CrawlConfig.from_dict(data)`.

Indexed pages:

- `add_page(page: IndexedPage) -> IndexedPage` — upsert keyed by `page.url`.
  On a URL collision the existing entry is replaced in place by
  `page.to_dict()`; otherwise appended. Returns the passed `page` (unmutated).
- `get_pages() -> list[IndexedPage]` — all pages as `IndexedPage` objects
  (via `IndexedPage.from_dict`); returns `[]` if the file is not a list.
- `get_page(url: str) -> IndexedPage | None` — first page with `url == url`,
  else `None`.
- `remove_page(url: str) -> bool` — drops every entry whose `url` matches;
  returns `True` if at least one was removed, `False` otherwise.
- `get_page_count() -> int` — `len` of the pages list (re-reads the file).
- `clear_pages()` — overwrites `pages.json` with `[]`.
- `get_stats() -> dict` — exactly the keys `total_interests`,
  `enabled_interests` (count where `enabled` is true), `total_pages`,
  `total_content_bytes` (sum of `content_length`), `data_dir` (str of the
  path).

## Contract Holes

Primary hole (ARCH-40): the write path is non-atomic and the read path
silently recovers from corruption by returning the empty default.
`_write_json` writes directly to the target file with no temp-file-and-rename
and no backup of the previous contents, so an interrupted write (process
crash, disk full, power loss) leaves a **truncated/partial JSON file** on
disk. The next `_read_json` then hits `json.JSONDecodeError` and — with no
error, no log, no `.bak` fallback — returns `[]` (for interests/pages) or `{}`
(for config), which `get_interests`/`get_pages`/`get_config` surface as an
**empty store**. The entire persisted dataset is destroyed with no signal to
the caller: a crash mid-`add_page` on a 10,000-page index silently reads back
as zero pages. The fix must make the write atomic (write to a temp file in the
same directory, `os.replace` onto the target, and keep the previous file as a
recoverable backup) and make corruption recovery explicit (on
`JSONDecodeError`, attempt the backup before returning the empty default, and
surface the corruption rather than silently returning an empty store).

Secondary holes (documented, not ticketed):

- `add_interest`/`add_page` are full-replace upserts: an `add` of a bare
  record (e.g. `IndexedPage(url=...)`) clobbers every other field of the
  existing record with its defaults — there is no field-level merge.
- `remove_interest`/`remove_page` drop **every** matching entry (a list
  filter), so if duplicate names/URLs ever exist all of them are removed,
  while `add_*` only replaces the first match — the two paths disagree on
  multiplicity.
- `list_interests` omits `priority`, `interest_type`, `value`, `topic`, and
  `match_mode`, so a round-trip through `list_interests` cannot reconstruct
  the stored `Interest`.
