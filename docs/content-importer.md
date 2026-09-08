# Content Importer (spec)

`personal_index.content_importer` — the "import" component that turns a raw
string in one of five formats into a list of item dicts. It is exported from
the package root as `ContentImporter` (`personal_index/__init__.py`) and is
distinct from the separate `personal_index/importer.py` (`Importer` /
`ImportResult`) module, which is a different, file-oriented importer and is
**not** covered by this page.

`ContentImporter` does **no network I/O** and **no file I/O** — it only parses
an in-memory string. The caller supplies the bytes/text and the format name.

The module exports one name: `ContentImporter`.

## Public API

### `ContentImporter`

Stateful only in that it carries a monotonically-increasing `_id_counter`
(starts at `0`) used to mint `id` values for items that do not supply their
own. Each `ContentImporter` instance numbers independently from 1.

Class constant:
- `SUPPORTED_FORMATS = ("json", "html", "markdown", "rss", "csv")`

#### `import_content(data: str, fmt: str) -> list[dict[str, Any]]`
The single public entry point.
- **Normalization:** `fmt` is normalized with `fmt.lower().strip()` before use,
  so `"JSON"`, `"  json  "`, `"Json"` all dispatch to the JSON handler.
- **Guard path (unsupported format):** if the normalized `fmt` is not in
  `SUPPORTED_FORMATS`, raises `ValueError("Unsupported format: {fmt}.
  Supported: {SUPPORTED_FORMATS}")`.
- **Dispatch:** otherwise dispatches to the private `_import_{fmt}` handler and
  returns that handler's list of item dicts **unchanged** (no further
  normalization at this level — see contract hole 1).

#### `batch_import(data_sources) -> list[dict[str, Any]]`
Imports from multiple sources and concatenates the results in order.
- `data_sources` is a list of `(data_str, format)` tuples; each is passed to
  `import_content` and the returned items are extended into one flat list.
- **Contract hole 2:** the parameter is **untyped** (no annotation) and the
  error contract is implicit — if any one source raises (unsupported format,
  malformed JSON, malformed XML), the whole call aborts and **all items from
  earlier sources are discarded** (no partial result, no per-source isolation).

### Private handlers (documented because they define the per-format item shape)

Each `_import_{fmt}` returns `list[dict[str, Any]]`. **The item key sets are
NOT uniform across formats** (contract hole 1):

- `_import_json(data)` — `json.loads`; a top-level JSON **object** is wrapped
  into a one-element list; a JSON **array** is used as-is. The result is
  routed through `_normalize_items`, so **only JSON items** carry the full
  normalized key set (see below). Malformed JSON raises
  `ValueError("Malformed JSON: ...")`.
- `_import_html(data)` — first tries `<article>...</article>` blocks
  (`_parse_html_article`); if **no** article is found, falls back to pairing
  `<h2>` headings with `<p>` paragraphs by index.
  - Article item keys: `title`, `description`, `link`, `id` (title defaults to
    `"Untitled"` when no `<h2>`; `link` is `""` when no `<a href>`).
  - Fallback item keys: `title`, `description`, `id` — **no `link` key at all**
    (contract hole 1).
- `_import_markdown(data)` — splits on lines; a heading line
  (`#{1,6} <title>` or `#{1,6} [text](url)`) starts a new item; subsequent
  non-heading, non-empty lines accumulate into that item's `description`.
  Item keys: `title`, `link`, `id` (plus `description` set at flush time).
  `link` is `""` for a plain (non-linked) heading.
- `_import_rss(data)` — parses with **stdlib** `xml.etree.ElementTree`
  (`ET.fromstring`), **not** `defusedxml` (contract hole 3). Walks
  `.//channel/item`; item keys: `title`, `description`, `link`, `id` where
  `id` is the `<guid>` text, falling back to a minted `_next_id()` when guid is
  absent/empty. `title` defaults to `"Untitled"`.
- `_import_csv(data)` — `csv.DictReader` over the string; each row becomes an
  item with **only the non-empty header columns** preserved, plus a minted
  `id` via `setdefault` when the row has no `id` column. Item keys therefore
  depend entirely on the CSV header (contract hole 1).

### `_normalize_items(items) -> list[dict[str, Any]]`
The **only** path that produces a uniform item shape. For each `dict` item it
emits exactly these keys:
- `title` (default `"Untitled"`), `description` (default `""`), `link`
  (default `""`), `id` (default minted `_next_id()`), `tags` (default `[]`),
  `date` (default `None`).
Non-dict entries in the input list are **skipped** (dropped silently).
**Contract hole 4:** a JSON scalar (e.g. `"123"` → `123`) is not a dict and is
skipped here, but a JSON input that is neither a dict nor a list (a bare
string/number) is wrapped by `_import_json` only when it is a dict — a bare
scalar reaches `_normalize_items` as a non-list and raises `TypeError` (not
`ValueError`) from the `for item in items` iteration.

### `_next_id() -> int`
Increments and returns the instance `_id_counter` (1, 2, 3, ...).

## Contract holes

1. **Inconsistent item shape across formats.** Only `_import_json` routes
   through `_normalize_items`, so only JSON items are guaranteed the
   `title/description/link/id/tags/date` key set. RSS/CSV/HTML/Markdown each
   emit their own ad-hoc key sets: the HTML fallback path omits `link`
   entirely, and **no** non-JSON format ever includes `tags` or `date`. A
   downstream consumer that assumes the normalized shape will `KeyError` on
   non-JSON imports. (Most important hole — ticketed as **ARCH-24**.)
2. **`batch_import` is untyped and aborts on first error.** No parameter
   annotation; a single bad source raises and discards all items collected
   from earlier sources (no partial result, no per-source isolation).
3. **`_import_rss` uses stdlib `ElementTree`, not `defusedxml`.** The sibling
   `personal_index.rss` module parses with `defusedxml`; the importer's RSS
   path parses untrusted XML with the stdlib parser (no XML-bomb / entity
   protection), and contains a dead `item.find("pubDate")` line whose result
   is discarded.
4. **JSON scalar input raises `TypeError`, not `ValueError`.** A bare JSON
   scalar (neither object nor array) is not wrapped and reaches
   `_normalize_items` as a non-list, raising `TypeError` from iteration
   instead of the `ValueError` the module uses for every other malformed-input
   path (malformed JSON, unsupported format).

## Tests
`tests/test_content_importer.py` pins the happy paths for all five formats
(list/single-dict/empty JSON, tags, missing fields, case-insensitive format;
CSV basic/empty/custom headers; HTML articles/multiple/link/fallback/empty;
Markdown basic/links/empty/multiline/h1; RSS basic). It does **not** pin the
cross-format shape inconsistency (hole 1), the `batch_import` error contract
(hole 2), or the JSON-scalar `TypeError` (hole 4).
