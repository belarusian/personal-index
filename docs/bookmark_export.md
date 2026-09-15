# bookmark_export — Exact Contract

Module: `personal_index/bookmark_export.py` (211 lines)

> **Disambiguation:** this page documents `personal_index.bookmark_export`
> (`BookmarkExporter` / `BookmarkExportResult`). It is a DIFFERENT module from
> `personal_index.bookmarks` (see [bookmarks.md](bookmarks.md) — the
> `Bookmark`/`BookmarkManager` store) and from
> `personal_index.content_exporter` (see [content-exporter.md](content-exporter.md)
> — `ContentExporter`). `BookmarkExporter` consumes a list of `Bookmark`
> objects (from `personal_index.bookmarks`) and renders them; it does not
> store or manage them.

Exports saved bookmarks to three string formats (JSON, Netscape HTML, OPML 2.0)
and to a file. Two public types: `BookmarkExportResult` (a `@dataclass`) and
`BookmarkExporter` (a plain class holding a `list` of `Bookmark`). There is no
locking; the exporter is single-threaded by contract.

## Public API

### BookmarkExportResult

A `@dataclass` with five fields (all defaulted, order matters for positional
construction):

- `format: str = ""`
- `bookmark_count: int = 0`
- `output_path: str = ""`
- `exported_at: str = ""`
- `errors: list[str] = field(default_factory=list)`

Behavior:

- `__post_init__`: if `exported_at` is empty it is set to
  `datetime.now(timezone.utc).isoformat()`. An explicit `exported_at` is kept
  as given — no parsing, no validation.
- On the failure paths of `export_to_file` the result is constructed with only
  `errors=[...]`, so `format` stays `""`, `bookmark_count` stays `0`, and
  `output_path` stays `""`. Callers must test `result.errors` (non-empty ==
  failure), NOT `result.format`/`result.bookmark_count`, to detect failure.

### BookmarkExporter

`__init__(self, bookmarks: list)` — stores the list as-is (no copy, no
validation; elements are expected to be `personal_index.bookmarks.Bookmark`
with a `.to_dict()` and `.title`/`.url` attributes).

`SUPPORTED_FORMATS: ClassVar[set[str]] = {"json", "html", "opml"}`.

String renderers (each returns a `str`, never raises on the bookmark data):

- `export_json() -> str` — `json.dumps([b.to_dict() for b in bookmarks],
  indent=2, ensure_ascii=False)`. A JSON array; empty list -> `[]`. Unicode is
  preserved (`ensure_ascii=False`).
- `export_html() -> str` — a Netscape bookmark file. Header is a fixed
  `<!DOCTYPE NETSCAPE-Bookmark-file-1>` + META + `<TITLE>`/`<H1>` + `<DL><p>`.
  One `<DT><A HREF="{href}" ADD_DATE="{now}">{display_title}</A>` per bookmark,
  where `href` and `display_title` are run through `_escape_html` (escapes
  `& < > "` only — NOT `'`). `display_title` falls back to `b.url` when
  `b.title` is falsy. `ADD_DATE` is a single `now` timestamp
  (`%Y%m%d%H%M%S`) shared by every bookmark in the file. Footer is
  `</DL><p>` + `</DL>`.
- `export_opml() -> str` — an OPML 2.0 document. `<?xml ...?>` + `<opml
  version="2.0">` + a `<head>` (fixed `<title>Bookmarks</title>` and
  `dateCreated`/`dateModified` from one shared `now`, `%Y-%m-%dT%H:%M:%SZ`) +
  a `<body>` with one
  `<outline text="{display_title}" htmlUrl="{url}" type="bookmark"/>` per
  bookmark. `text` and `htmlUrl` are run through `_escape_xml` (escapes
  `& < > " '` — the full XML set). `text` falls back to `b.url` when `b.title`
  is falsy.

Dispatch / file I/O:

- `export(self, fmt: str) -> str | None` — lowercases `fmt`, then returns
  `export_json()` / `export_html()` / `export_opml()` for `"json"`/`"html"`/
  `"opml"`, and `None` for anything else. Case-insensitive.
- `export_to_file(self, filepath: str, fmt: str | None = None) ->
  BookmarkExportResult` — always returns a `BookmarkExportResult`, never
  `None`, never raises for the unsupported-format or write-failure cases.
  Format resolution: if `fmt is None` it is derived from the file extension via
  the module-level `_EXTENSION_MAP = {"json": "json", "html": "html",
  "htm": "html", "opml": "opml"}` (extension lowercased, leading dot stripped);
  an explicit `fmt` is used as-is (NOT lowercased here, but `export()`
  lowercases it downstream). On success the file is written UTF-8 and the
  result carries `format`, `bookmark_count=len(bookmarks)`, `output_path`.

## Invariants

- The three string renderers never raise on bookmark data; escaping is applied
  to every interpolated title/url.
- `export_to_file` degrades to a `BookmarkExportResult` with non-empty
  `errors` for (a) an unsupported/undetectable format and (b) an `OSError`
  during the write — it does not propagate either.

## Persistence

None. The exporter is stateless beyond the `bookmarks` list it was given; it
writes only the single file named by `export_to_file` and reads nothing.

## Documented contract hole (ARCH-79)

`export_to_file`'s unsupported-format error message is not extension-aware.
When `fmt is None` and the file extension is not in `_EXTENSION_MAP` (e.g.
`bookmarks.txt`, `bookmarks.pdf`, `bookmarks.xyz`), lines 182-184 leave `fmt`
as `None`, and line 188 builds the message as
`f"Unsupported format: {fmt}"` — so the caller receives the literal string
`"Unsupported format: None"`. The message names the Python `None` sentinel, not
the extension that was actually inspected, so a caller cannot tell
"you gave a file with an unknown extension" apart from any other `None`-fmt
path, and the extension the user actually typed is lost. The existing tests
(`test_export_to_file_unsupported_extension`,
`test_export_to_file_never_returns_none`) only assert `len(result.errors) > 0`,
so the `"None"` wording is un-pinned.

**Not holes** (do not re-ticket): the explicit-`fmt` unsupported case
(`export_to_file(path, "pdf")` -> `"Unsupported format: pdf"`) is correctly
worded because `fmt` is a real string there; the `OSError` write-failure path
is correctly worded (`"Failed to write file: {filepath}: {exc}"`, pinned by
`test_export_to_file_returns_result_with_errors_on_write_failure`); the
HTML-vs-XML escaping difference (HTML omits `'`, OPML includes it) is a
deliberate per-format choice, not a defect, because both escape the characters
their respective formats require for the interpolated fields; and the shared
single `now` timestamp across all bookmarks in one file is by design (one
export = one moment).
