# ARCH-79 — bookmark_export: `BookmarkExporter.export_to_file` reports the literal `"Unsupported format: None"` for an unknown extension (not extension-aware)

Status: OPEN
Component: `personal_index/bookmark_export.py` — `BookmarkExporter.export_to_file` (lines 168-211); specifically the format-resolution block (lines 182-184) that leaves `fmt` as `None` when the extension is not in `_EXTENSION_MAP`, and the error construction at line 188 `errors=[f"Unsupported format: {fmt}"]` that interpolates the `None` sentinel.
Umbrella: ARCH-2 (#983)
Issue: #1434
Docs: `docs/bookmark_export.md` (Documented contract hole, ARCH-79)

## Problem
`export_to_file(self, filepath: str, fmt: str | None = None)` auto-detects the
format from the file extension when `fmt is None`:

    if fmt is None:                                   # line 182
        ext = Path(filepath).suffix.lstrip(".").lower()  # line 183
        fmt = _EXTENSION_MAP.get(ext)                 # line 184
    if fmt is None or fmt not in self.SUPPORTED_FORMATS:  # line 186
        return BookmarkExportResult(
            errors=[f"Unsupported format: {fmt}"]     # line 188
        )

`_EXTENSION_MAP = {"json": "json", "html": "html", "htm": "html", "opml":
"opml"}`. For any extension NOT in that map (e.g. `.txt`, `.pdf`, `.xyz`),
`_EXTENSION_MAP.get(ext)` returns `None`, so `fmt` stays `None`, and line 188
builds the message as `f"Unsupported format: {fmt}"` -> the literal string
**`"Unsupported format: None"`**. The message names the Python `None` sentinel,
not the extension the caller actually typed, so:

- a caller cannot tell "you gave a file with an unknown extension" apart from
  any other `None`-fmt path;
- the extension the user actually supplied (`.txt`, `.pdf`, ...) is lost from
  the error.

Verified (cycle 247):

    e = BookmarkExporter([Bookmark(url="http://a.com", title="A")])
    e.export_to_file("/tmp/bookmarks.txt")
    # -> BookmarkExportResult(format="", bookmark_count=0, output_path="",
    #                         errors=["Unsupported format: None"])
    e.export_to_file("/tmp/bookmarks.pdf")
    # -> errors=["Unsupported format: None"]   (same string, .pdf lost)
    # contrast the explicit-fmt path, which IS correctly worded:
    e.export_to_file("/tmp/x.pdf", "pdf")
    # -> errors=["Unsupported format: pdf"]

This is surprising/lossy where a caller would reasonably expect the error to
name the extension that was inspected. No existing test pins the wording:
`test_export_to_file_unsupported_extension` and
`test_export_to_file_never_returns_none` only assert `len(result.errors) > 0`,
so the `"None"` wording is un-pinned.

## What is NOT a hole (do not re-ticket)
- The **explicit-`fmt`** unsupported case (`export_to_file(path, "pdf")` ->
  `"Unsupported format: pdf"`) is correctly worded because `fmt` is a real
  string there; only the auto-detect (`fmt is None`) path produces `"None"`.
- The **`OSError` write-failure** path is correctly worded
  (`"Failed to write file: {filepath}: {exc}"`) and is pinned by
  `test_export_to_file_returns_result_with_errors_on_write_failure`.
- The **HTML-vs-XML escaping difference** (`_escape_html` omits `'`;
  `_escape_xml` includes it) is a deliberate per-format choice, not a defect:
  both escape every character their format requires for the interpolated
  title/url fields.
- The **shared single `now` timestamp** across all bookmarks in one file
  (one `ADD_DATE` / one `dateCreated`+`dateModified`) is by design: one export
  is one moment.
- `export_to_file` never returning `None` / never raising for the
  unsupported-format and write-failure cases is correct and pinned
  (`test_export_to_file_never_returns_none`).

## Public contract (recommended)
`export_to_file(self, filepath: str, fmt: str | None = None) ->
BookmarkExportResult`:
- Success path: unchanged (write UTF-8, return result with `format`,
  `bookmark_count`, `output_path`).
- Explicit-`fmt` unsupported path: unchanged — `errors=["Unsupported format:
  {fmt}"]` where `{fmt}` is the caller's string (e.g. `"pdf"`).
- **Auto-detect unsupported path (the hole):** when `fmt is None` and the
  extension is not in `_EXTENSION_MAP`, the error must name the inspected
  extension, e.g. `errors=["Unsupported format: txt (from extension)"]` or
  `errors=["Unsupported format: .txt"]` — NOT the literal `"None"`. The exact
  wording is the implementer's choice, but it MUST (a) not contain the bare
  token `None` and (b) include the extension string that was actually derived
  from `filepath`.
- `OSError` write-failure path: unchanged.

## Acceptance criteria
1. `export_to_file("/tmp/bookmarks.txt")` (no explicit `fmt`, unknown
   extension) returns a `BookmarkExportResult` whose `errors[0]` does NOT
   contain the bare token `None` and DOES contain the extension `"txt"`.
2. `export_to_file("/tmp/bookmarks.pdf")` (no explicit `fmt`) returns
   `errors[0]` containing `"pdf"` and not `None` (distinct from the `.txt`
   message — the extension is preserved).
3. `export_to_file("/tmp/x.pdf", "pdf")` (explicit `fmt`) still returns
   `errors[0] == "Unsupported format: pdf"` (explicit path unchanged; existing
   `test_export_to_file_unsupported_format` stays green).
4. `export_to_file("/tmp/ok.json", "json")` and the auto-detect
   `.json`/`.html`/`.htm`/`.opml` success paths are unchanged (existing
   `test_export_to_file_json/html/opml/auto_detect_*` stay green).
5. The `OSError` write-failure path is unchanged (existing
   `test_export_to_file_returns_result_with_errors_on_write_failure` stays
   green).

## Pinning tests to add (tests/test_bookmark_export.py)
- **The hole (auto-detect, unknown extension):**
  `exporter.export_to_file(str(tmp_path / "bookmarks.txt"))` — assert
  `result is not None`, `len(result.errors) == 1`,
  `"None" not in result.errors[0]`, and `"txt" in result.errors[0]`. Pins the
  corrected, extension-aware message against the returned object, not the
  docstring.
- **Guard path (auto-detect, a second unknown extension):**
  `exporter.export_to_file(str(tmp_path / "bookmarks.pdf"))` — assert
  `"pdf" in result.errors[0]` and `"None" not in result.errors[0]`. Confirms
  the message tracks the actual extension rather than being a fixed string.
- **Normal case (explicit fmt, unchanged):**
  `exporter.export_to_file(str(tmp_path / "x.pdf"), "pdf")` — assert
  `result.errors[0] == "Unsupported format: pdf"`. Confirms the fix does not
  over-reach into the explicit-`fmt` path.

## Docs (SAME PR)
`docs/bookmark_export.md` (new, spec) + the `bookmark_export.md` index entry in
docs/README.md ship in the same PR as this ticket.
