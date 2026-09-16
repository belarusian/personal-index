# ARCH-80 — content_export_csv: `CSVExporter.export_to_file` hardcodes `encoding="utf-8"` and silently drops the caller's `encoding` kwarg (lossy, no signal)

Status: IMPLEMENTED #1538@fdb2d88 (cycle 308)
Component: `personal_index/content_export_csv.py` — `CSVExporter.export_to_file` (lines 191-200); specifically line 198 `content = self.export(items, **kwargs)` (forwards the caller's `encoding` into `export()`, where the parameter at line 80 is accepted but never read) and line 199 `with open(filepath, "w", encoding="utf-8") as f:` (hardcoded utf-8, the `encoding` kwarg never reaches this `open()`).
Umbrella: ARCH-2 (#983)
Issue: #1436
Docs: `docs/content_export_csv.md` (Documented contract hole, ARCH-80)

## Problem
`export_to_file(self, items, filepath, **kwargs)` is the only I/O path on
`CSVExporter`. It does:

    content = self.export(items, **kwargs)          # line 198
    with open(filepath, "w", encoding="utf-8") as f:  # line 199
        f.write(content)                            # line 200

`export()` (line 67) declares `encoding: str = "utf-8"` (line 80) but **never
reads it** — the method returns a `str`, so there is no encoding to apply. The
caller's `encoding` kwarg is therefore forwarded into `export()` and silently
discarded, and the file is ALWAYS written as utf-8.

Consequence: a caller requesting a non-utf-8 encoding gets a utf-8 file with
no error, no warning, and no signal — the request is lossy.

Verified (cycle 248):

    e = CSVExporter()
    items = [{"id": "1", "title": "café"}]   # 'é' is U+00E9
    e.export_to_file("/tmp/out.csv", encoding="latin-1")
    # -> file bytes are UTF-8 (b'\xc3\xa9' for 'é'), NOT latin-1 (b'\xe9').
    #    The encoding="latin-1" request is silently dropped.
    # contrast: the sibling personal_index/content_export/csv_export.py:102
    #   filepath.write_text(content, encoding=self.options.encoding)
    # DOES honor the requested encoding — so this module's hardcoded utf-8 is
    # a genuine divergence, not a house-wide convention.

This is surprising/lossy where a caller would reasonably expect the requested
encoding to be honored (or, at minimum, to be rejected with a signal). No
existing test pins the non-default path:
`tests/test_content_export_csv.py::test_export_with_encoding` (line 257) passes
`encoding="utf-8"` (the default), so the lossy non-utf-8 path is un-pinned.

## What is NOT a hole (do not re-ticket)
- `export()` returning a `str` and ignoring `encoding` is *by itself* not a
  bug — a string has no encoding. The hole is specifically that
  `export_to_file` advertises (via `**kwargs`) an encoding it then discards on
  the `open()` call.
- The **unrecognized-`export_format` fall-through to CSV** (line 65, the final `return self._export_csv(...)` in `_dispatch_format`) is a deliberate degrade, not a raise; it is documented in `docs/content_export_csv.md` and is not the subject of ARCH-80.
- The **negative-`limit` clamp to 0** (lines 90-92) is documented in the
  `export()` docstring and pinned by existing tests; it is not a hole.
- `get_stats` returning a plain `dict` (not the `ExportStats` dataclass) is a
  dead-type observation (noted under `ExportStats` in the docs page), not a
  behavioral defect.
- The sibling `personal_index/content_export/csv_export.py` honoring
  `self.options.encoding` is the CORRECT behavior this module should match —
  it is the reference, not a defect.

## Public contract (recommended)
`export_to_file(self, items: list[dict], filepath: str, **kwargs) -> None`:
- **Honor the requested encoding (the fix):** extract `encoding` from `kwargs`
  (default `"utf-8"`), forward the REMAINING kwargs to `self.export(items,
  **kwargs)`, and write the file with
  `open(filepath, "w", encoding=encoding)`. The exact mechanism (pop from
  kwargs vs. an explicit `encoding` parameter) is the implementer's choice, but
  the observable contract MUST be: the file's byte encoding equals the
  `encoding` the caller requested (default utf-8 when omitted).
- **Default path unchanged:** with no `encoding` kwarg the file is utf-8
  (existing `test_export_to_file` / `test_export_to_file_overwrite` stay green).
- `export()`'s signature and behavior are unchanged (it still returns a `str`
  and still ignores its own `encoding` parameter — that is not the hole).

## Acceptance criteria
1. `export_to_file(items, path)` with NO `encoding` kwarg writes a utf-8 file
   (existing `test_export_to_file` and `test_export_to_file_overwrite` stay
   green).
2. `export_to_file(items, path, encoding="latin-1")` writes a file whose bytes
   decode as latin-1 and are NOT the utf-8 encoding of the same content — i.e.
   the requested encoding is honored (the hole).
3. `export_to_file(items, path, encoding="utf-8")` writes a utf-8 file (the
   explicit-default path is unchanged).
4. `export_to_file` still forwards the other kwargs to `export()` (e.g.
   `export_format=ExportFormat.JSON` produces a JSON file) — the fix must not
   swallow non-encoding kwargs.
5. `export()` itself is unchanged: `export(items, encoding="latin-1")` still
   returns the same `str` as `export(items)` (the parameter remains inert on
   the string path).

## Pinning tests to add (tests/test_content_export_csv.py)
- **The hole (non-default encoding honored):**
  `items = [{"id": "1", "title": "café"}]`;
  `exporter.export_to_file(items, str(tmp_path / "out.csv"), encoding="latin-1")`
  — read the file bytes and assert they equal
  `("id,title\n1,café\n".encode("latin-1"))` (i.e. `'é'` is the single byte
  `b'\xe9'`, NOT the two-byte utf-8 `b'\xc3\xa9'`). Pins the honored encoding
  against the actual file bytes, not the docstring.
- **Guard path (default encoding unchanged):**
  `exporter.export_to_file(items, str(tmp_path / "out2.csv"))` (no `encoding`)
  — assert the file bytes equal the utf-8 encoding of the same content
  (`'é'` is `b'\xc3\xa9'`). Confirms the fix does not change the default.
- **Normal case (other kwargs still forwarded):**
  `exporter.export_to_file(items, str(tmp_path / "out.json"),
  export_format=ExportFormat.JSON)` — assert the file content is valid JSON
  (starts with `[`), confirming the fix does not swallow non-encoding kwargs.

## Docs (SAME PR)
`docs/content_export_csv.md` (new, spec) + the `content-export-csv.md` index
entry in docs/README.md ship in the same PR as this ticket.
