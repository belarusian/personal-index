# Importer (spec)

`personal_index.importer` — the **file-oriented** bookmark importer. It is a
separate module from `personal_index.content_importer` (covered by
[content-importer.md](content-importer.md)): that one turns an in-memory string
into a list of item *dicts*; this one parses a file or string into
`Bookmark` objects and writes them into a `BookmarkManager`.

The module exports two names: `ImportResult` (a dataclass) and `Importer`.
It does **no network I/O**; the only file I/O is the single `open()` inside
`import_from_file`. XML/HTML parsing uses `defusedxml.ElementTree` (never the
stdlib parser) for the XML/OPML/HTML-fallback paths, and `BeautifulSoup`
(`html.parser`) for the primary HTML path.

## Public API

### `ImportResult`
A `@dataclass` describing the outcome of one import operation.

Fields (all have defaults):
- `total_imported: int = 0` — count of `Bookmark`s written to the manager.
- `total_skipped: int = 0` — count of items with an empty `url` that were
  counted as skipped (see contract hole 1 — not all formats set this).
- `errors: list[str] = field(default_factory=list)` — accumulated per-item /
  per-parse error strings.
- `source: str = ""` — the source path or label passed in.
- `format: str = ""` — the format name the handler ran under.
- `imported_at: str = ""` — ISO-8601 UTC timestamp.

`__post_init__`: if `imported_at` is falsy it is set to
`datetime.now(timezone.utc).isoformat()`.

### `Importer`
Stateful only in that it holds a `BookmarkManager` (created on demand).

Class constant:
- `SUPPORTED_FORMATS: ClassVar[set[str]] = {"json", "csv", "html", "xml",
  "necko", "netscape"}` — note **`"opml"` is NOT in this set** (see contract
  hole 2).

#### `__init__(self, manager: BookmarkManager | None = None) -> None`
Stores `manager` if given, else creates a fresh `BookmarkManager()`.

#### `manager` (property) -> `BookmarkManager`
Returns the stored manager.

#### `import_from_file(self, filepath: str) -> ImportResult`
Dispatches on the file's extension.
- **Guard path (missing file):** `Path(filepath)` does not exist → returns
  `ImportResult(errors=[f"File not found: {filepath}"], source=filepath)`
  (no `format` set).
- **Guard path (unsupported extension):** `ext = path.suffix.lstrip(".").lower()`
  not in `SUPPORTED_FORMATS` → returns
  `ImportResult(errors=[f"Unsupported format: {ext}"], source=filepath,
  format=ext)`.
- **Normal path:** opens the file (utf-8), reads its content, and delegates to
  `import_from_content(content, ext, source=filepath)`, returning that result
  unchanged. No direct manager writes at this level.

#### `import_from_content(self, content: str, fmt: str, source: str = "") -> ImportResult`
The string entry point.
- **Normalization:** `fmt = fmt.lower().lstrip(".")` (so `"JSON"`, `".csv"`,
  `"Html"` all match).
- **Dispatch:** `"json"` → `_import_json`; `"csv"` → `_import_csv`;
  `"html"`/`"necko"`/`"netscape"` → `_import_html`; `"xml"` → `_import_xml`.
- **Guard path (no match):** returns
  `ImportResult(errors=[f"Unsupported format: {fmt}"], source=source,
  format=fmt)` with `total_imported`/`total_skipped` at 0. Note `"opml"`
  reaches this guard — `import_opml` is only reachable by direct call (see
  contract hole 2).

#### `_import_json(self, content: str, source: str = "") -> ImportResult`
- **Guard path (malformed JSON):** `json.JSONDecodeError` → appends
  `"Invalid JSON: ..."` to `errors` and returns early (zero items).
- A top-level JSON **object** (dict) is wrapped into a single-element list so
  dict and array inputs are handled uniformly.
- Per item: builds a `Bookmark` from `url`/`title`/`description`/`category`
  (default `"imported"`)/`tags` (default `[]`)/`is_favorite` (default
  `False`). If `bookmark.url` is non-empty → `manager.add` + `total_imported`
  += 1; if empty → `total_skipped` += 1 (no write).
- A per-item `(ValueError, TypeError)` is caught, appended to `errors` as
  `"Error importing item: ..."`, and the loop continues.

#### `_import_csv(self, content: str, source: str = "") -> ImportResult`
- Iterates `csv.DictReader` rows over `content` (via `StringIO`).
- Per row: builds a `Bookmark` using **case-insensitive header fallback**
  (`url`/`URL`, `title`/`Title`, `description`/`Description`,
  `category`/`Category` default `"imported"`, `tags`/`Tags` comma-split and
  stripped, `favorite`/`Favorite` lowercased and compared to `"true"`).
- Non-empty `url` → `manager.add` + `total_imported` += 1; empty `url` →
  `total_skipped` += 1.
- A per-row `(ValueError, TypeError)` is caught, appended to `errors` as
  `"Error importing row: ..."`, and the loop continues.

#### `_import_html(self, content: str, source: str = "") -> ImportResult`
- **Guard path (not HTML):** `content.strip()` does not start with `"<"` or
  lacks `">"` → appends `"Invalid HTML: content does not appear to be HTML"`
  and returns early.
- **Primary path (BeautifulSoup):** `BeautifulSoup(content, "html.parser")`;
  iterates `soup.find_all("a", href=True)` and, per anchor, builds a
  `Bookmark(url=href, title=title-attr-or-text, category="imported")`, adds it
  to the manager, and increments `total_imported`.
- **Fallback path (no bs4):** on `ImportError` from the bs4 import, parses with
  `ET_fromstring` (appending `"Invalid HTML/XML: ..."` on `ET_ParseError` and
  returning early) and walks the tree via `_parse_html_element`.
- **Note:** the HTML path never increments `total_skipped` — an `<a>` with no
  `href` is simply not matched by `find_all("a", href=True)` (see contract
  hole 1).

#### `_parse_html_element(self, element, result: ImportResult, path: list[str]) -> None`
Recursively walks the ElementTree fallback tree.
- Reads `element.tag` (lowercased). Only when it equals `"a"` does it read the
  `href` attribute (default `""`) and the `title` attribute (falling back to
  `element.text` or `""`); a `Bookmark(url=href, title=title,
  category="imported")` is added to the manager and `total_imported` += 1
  **only when `href` is truthy** — an `<a>` with no `href` is silently skipped
  (no `total_skipped` increment, no error).
- Every child is recursed into. The `path` parameter is **accepted but never
  used** (see contract hole 3). Returns `None`; mutates `result` and the
  manager in place.

#### `_import_xml(self, content: str, source: str = "") -> ImportResult`
- **Guard path (malformed XML):** `ET_ParseError` → appends `"Invalid XML:
  ..."` and returns early.
- Iterates `root.findall(".//bookmark")`. Per element: extracts `url`
  (attribute or `<url>` child), `title`, `description`, `category` (default
  `"imported"`), and `tags` (comma-split, whitespace-stripped, empties
  dropped). Non-empty `url` → `manager.add` + `total_imported` += 1; empty
  `url` → `total_skipped` += 1.
- A per-element `(ValueError, TypeError)` is caught, appended to `errors` as
  `"Error parsing bookmark element: ..."`, and the loop continues.

#### `import_opml(self, content: str, source: str = "") -> ImportResult`
- **Guard path (malformed OPML):** `ET_ParseError` → appends `"Invalid OPML:
  ..."` and returns early.
- Iterates `root.findall(".//outline[@text]")` (only outlines carrying a
  `text` attribute). Per outline: `url` = `xmlUrl` attribute (falling back to
  `htmlUrl`, then `""`); `title` = `title` attribute (falling back to `text`,
  then `""`). When `url` is truthy → `manager.add` + `total_imported` += 1.
  When `url` is falsy → **no bookmark and no counter increment** (see contract
  hole 1).
- **Reachability:** this method is **not** reachable through
  `import_from_content` / `import_from_file` (see contract hole 2).

## Contract holes
1. **`total_skipped` accounting is inconsistent across formats.** JSON, CSV,
   and XML increment `total_skipped` for items with an empty `url`, but the
   HTML path (both the BeautifulSoup and the `_parse_html_element` fallback)
   and the OPML path **silently drop** empty-`url` items — no `total_skipped`
   increment and no `errors` entry. A consumer that assumes
   `total_imported + total_skipped == total_items_seen` gets correct
   accounting for JSON/CSV/XML but under-counts for HTML/OPML. (Most important
   hole — ticketed as **ARCH-25**.)
2. **`import_opml` is unreachable via the public dispatch.** `"opml"` is not in
   `SUPPORTED_FORMATS`, so `import_from_content("...", "opml")` returns the
   `"Unsupported format: opml"` guard result and `import_from_file` on a
   `.opml` file returns `"Unsupported format: opml"`. OPML is importable only
   by calling `import_opml` directly — the format is advertised in the module
   docstring's "various formats" but not in the dispatch contract.
3. **`_parse_html_element`'s `path` parameter is dead.** It is accepted and
   threaded through every recursive call but never read; the method's contract
   does not depend on it.
4. **Stray dead docstring at end of module.** After `import_opml` there is a
   bare module-level string literal `"""Result of an import operation."""`
   (line 357) that is not attached to any object — a leftover from a moved
   `ImportResult` docstring.

## Tests
`tests/test_importer.py` pins the happy paths and guard paths for all formats
(ImportResult defaults/custom/manager property; `SUPPORTED_FORMATS`; JSON
list/single-dict/invalid/empty-url/all-fields/per-item-error-continues; CSV
basic/favorites/empty-url/case-insensitive-headers; HTML basic/title-attr/
invalid/nested/`_parse_html_element` fields; XML basic/invalid/empty-url/
tags-accounting; OPML basic/invalid/title-attr; file not-found/unsupported/
error-path fields; `import_from_content` json/csv/unsupported; defusedxml
usage). It does **not** pin the cross-format `total_skipped` inconsistency
(hole 1), the OPML dispatch unreachability (hole 2), the dead `path` param
(hole 3), or the stray trailing docstring (hole 4).
