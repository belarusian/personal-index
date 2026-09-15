# export — Exact Contract

Module: `personal_index/export.py` (235 lines, stdlib-only imports: `csv`,
`json`, `dataclasses`, `datetime`, `io`, `pathlib`, `typing`; plus
`personal_index.bookmarks.BookmarkManager`).

Bookmark export to six file formats. Two public types: `ExportResult` (a
5-field `@dataclass` result record) and `Exporter` (the engine:
`export_to_file`, `export_to_content`, `export_filtered`, and the `manager`
accessor). `Exporter` renders the bookmarks held by a `BookmarkManager` into
one of six string formats — `json`, `csv`, `html`, `xml`, `markdown`, `opml` —
selected by the `fmt` argument. `export_to_content` returns a `str` (or `None`
on an unsupported format); `export_to_file` writes that string to a
caller-supplied path and returns an `ExportResult`.

> **Disambiguation (near-name collision):** This page documents
> `personal_index.export` (module `personal_index/export.py`, public types
> `Exporter` / `ExportResult`). It is **DIFFERENT** from:
> - `personal_index.content_exporter` (see [content-exporter.md](content-exporter.md), class `ContentExporter`)
> - `personal_index.content_export_csv` (see [content-export-csv.md](content-export-csv.md), class `CSVExporter`)
> - `personal_index.bookmark_export` (see [bookmark_export.md](bookmark_export.md), class `BookmarkExporter`)
> - the `personal_index/content_export/` subpackage (`csv_export` / `json_export` / `markdown_export`)
>
> Tests import from this module: `from personal_index.export import Exporter, ExportResult`
> (see `tests/test_export.py`, `tests/test_ticket111_private_bookmarks.py`).

## Public API

### ExportResult (dataclass, line 29)

Five fields, all defaulted:

- `total_exported: int = 0` — number of bookmarks written (from
  `BookmarkManager.count()` on the success path; `0` on the failure path).
- `output_path: str = ""` — the path written to (empty on the failure path).
- `format: str = ""` — the resolved format token (empty on the failure path).
- `exported_at: str = ""` — ISO-8601 UTC timestamp; `__post_init__` stamps
  `datetime.now(timezone.utc).isoformat()` when left empty.
- `errors: list[str] = field(default_factory=list)` — one message per failure
  (empty on success).

There is **no** `success` boolean: the caller distinguishes success from
failure by `errors` being empty (and `total_exported`/`output_path` being
populated).

### Exporter (class, line 41)

`SUPPORTED_FORMATS: ClassVar[set[str]] = {"json", "csv", "html", "xml",
"markdown", "opml"}` — the six normalized format tokens.

`__init__(self, manager: BookmarkManager | None = None) -> None`:

- `self._manager = manager or BookmarkManager()` — the injected manager, or a
  fresh default created when none is supplied.

`manager` property -> `BookmarkManager`:

- Read-only accessor for the manager this exporter operates on: the instance
  injected at construction, or the fresh default created in `__init__`.
  Returns the **same reference** on every call (no copy, no re-creation);
  pure.

`export_to_file(self, filepath: str, fmt: str | None = None) -> ExportResult`:

- If `fmt is None`, the format is auto-detected from the file extension via
  `EXTENSION_MAP` (`json`/`csv`/`html`/`htm`/`xml`/`md`/`markdown`/`opml`); an
  unrecognized extension returns
  `ExportResult(errors=[f"Unsupported format: {ext}"])` **without raising**.
- Otherwise calls `export_to_content(fmt)`; a `None` return (unsupported
  format) returns `ExportResult(errors=[f"Export failed for format: {fmt}"])`
  **without raising**.
- On success, writes the content to `filepath` with `encoding="utf-8"` and
  returns `ExportResult(total_exported=manager.count(), output_path=filepath,
  format=fmt)`.

`export_to_content(self, fmt: str) -> str | None`:

- Normalizes with `fmt = fmt.lower()` and dispatches to the private
  `_export_{fmt}` handler. An unsupported format returns `None` (does **not**
  raise).

`export_filtered(self, fmt: str, category: str | None = None, tag: str | None = None, favorites_only: bool = False) -> str | None`:

- Filters `manager.list_all()` by `category` (exact match), `tag` (membership
  in `b.tags`), and/or `favorites_only` (`b.is_favorite`); copies the matches
  into a fresh `BookmarkManager`, wraps it in a temporary `Exporter`, and
  returns `export_to_content(fmt)` on that filtered set. An unsupported `fmt`
  returns `None` (does **not** raise).

## Invariants

- `Exporter` **never raises** on an unsupported format: `export_to_file`
  returns an `ExportResult` with a populated `errors` list, and
  `export_to_content` / `export_filtered` return `None`.
- `export_to_file` writes with a hardcoded `encoding="utf-8"` (no caller
  encoding parameter exists on this method).
- The `manager` property is a pure, stable reference accessor.
- HTML and XML output escape special characters (`_escape_html` /
  `_escape_xml`); JSON uses `ensure_ascii=False`; CSV joins `tags` with `";"`.
- `export_filtered` is a **copy** path: it never mutates the source manager.

## Persistence

`export_to_file` writes to the caller-supplied `filepath` (UTF-8). The module
is a read-only consumer of the `BookmarkManager`; it does not persist or
mutate the manager's own backing store.

## Documented Contract Hole

**`_export_html` emits unbalanced `<DL>` tags (malformed Netscape HTML).**
`_export_html` (line 121) opens exactly one list container with
`'<DL><p>'` (line 128) but closes it with `lines.extend(["</DL><p>", "</DL>"])`
(line 136) — that is **two** `</DL>` closing tags for **one** opening `<DL>`.
The emitted document therefore has an unbalanced `<DL>`/`</DL>` pair: a strict
HTML parser (or a browser's DOM) sees one extra `</DL>` with no matching open,
so the Netscape bookmark file is structurally malformed. The existing HTML
tests (`test_export_html_content`, `test_export_html_escapes_special_chars`,
`test_export_html_file`) only assert substrings (the DOCTYPE, an `HREF`, and
escape entities) and never pin tag balance, so the defect is unpinned. See
ARCH-81 for the precise contract.

**Adjacent behaviors that are NOT holes** (do not re-ticket):
- Unsupported format in `export_to_file` / `export_to_content` /
  `export_filtered` degrades gracefully (no raise) — already pinned by
  `test_export_unsupported_format` and `test_export_to_content_unsupported`.
- The `manager` accessor is a pure, stable reference — already pinned by
  `TestExporterManager` (TICKET-514).
- HTML/XML escaping of `& < > "` (and `'` for XML) is correct — pinned by
  `test_export_html_escapes_special_chars` / `test_export_xml_escapes_special_chars`.
