# content_export_csv — Exact Contract

Module: `personal_index/content_export_csv.py` (213 lines)

> **Disambiguation:** this page documents `personal_index.content_export_csv`
> (`CSVExporter`). It is a DIFFERENT module from
> `personal_index.content_exporter` (see [content-exporter.md](content-exporter.md)
> — `ContentExporter`, the html/json/markdown/rss exporter) and from the
> `personal_index.content_export/` subpackage (`csv_export.py` / `json_export.py`
> / `markdown_export.py`, the `ContentExporter`-style options-based exporters).
> `CSVExporter` consumes a `list[dict]` of content items and renders them to a
> string (CSV/TSV/JSON/JSON-Lines) or to a file. It is a plain stateless class
> (no `__init__` state, no locking, no persistence); every method is a pure
> function of its arguments.

## Public API

### ExportFormat (Enum)

A `str`-Enum with four members: `CSV = "csv"`, `TSV = "tsv"`,
`JSON = "json"`, `JSON_LINES = "json_lines"`. Because it subclasses `str`,
`ExportFormat.CSV == "csv"` is `True`.

### ExportStats (dataclass)

A `@dataclass` with four defaulted fields: `total_items: int = 0`,
`exported_items: int = 0`, `columns: int = 0`, `format: str = "csv"`.

**Contract note (dead type):** `ExportStats` is defined but is NEVER
constructed or returned anywhere in the module or the test suite.
`get_stats` returns a plain `dict` (see below), not an `ExportStats`. It is a
vestigial public type; do not rely on it.

### CSVExporter

A plain class with no instance state (`__init__` is empty). Public methods:

- `export(items, columns=None, delimiter=",", quoting=csv.QUOTE_MINIMAL,
  include_header=True, column_names=None, filter_fn=None, sort_key=None,
  limit=None, offset=0, export_format=ExportFormat.CSV, encoding="utf-8") -> str`
- `export_to_file(items, filepath, **kwargs) -> None`
- `get_stats(items) -> dict`

#### export()

Behavior, in order:

1. `if not items: return ""` — an empty input list yields the empty string
   (no header, no rows), regardless of `include_header`.
2. `if offset < 0: offset = 0`
   — a **negative offset is clamped to 0** (all rows returned, identical to
   `offset=0`); then `filtered = self._apply_filter_sort(items, filter_fn, sort_key)[offset:]`
   — `filter_fn` (if given) is applied first, then `sort_key` (if given) sorts
   the filtered list, then the result is sliced from `offset`.
3. `if limit is not None: if limit < 0: limit = 0; filtered = filtered[:limit]`
   — a **negative limit is clamped to 0** (no rows emitted, identical to
   `limit=0`); a `None` limit means "no limit".
4. `if not filtered: return ""` — if filtering/offset/limit leaves zero rows,
   the empty string is returned (again, no header).
5. `if columns is None: columns = self._get_columns(filtered)` — column
   discovery is deferred until after filtering, so the header reflects only
   the columns present in the *exported* rows.
6. `col_map = column_names or {}` — `column_names` is a `{col: display_name}`
   rename map; missing keys fall back to the original column name.
7. Dispatch on `export_format` via `_dispatch_format`:
   - `CSV` -> `_export_csv(filtered, columns, delimiter, quoting, include_header, col_map)`
   - `TSV` -> `_export_csv(..., "\t", ...)` (delimiter forced to tab)
   - `JSON` -> `_export_json(filtered, columns, col_map)`
   - `JSON_LINES` -> `_export_json_lines(filtered, columns, col_map)`
   - **any other value** (e.g. a raw string that is not a member, or a
     subclassed value) falls through to the final `return self._export_csv(...)`
     — i.e. an unrecognized format silently degrades to CSV, it does NOT raise.

The `encoding` parameter (line 80) is **accepted but never read** by
`export()`: the method returns a `str`, so there is no encoding to apply. See
the Documented contract hole below.

#### _get_columns(items)

Collects the union of all keys across `items`, then orders them: first the
`DEFAULT_COLUMNS` that are present (in that fixed order — `id, title, url,
content_type, created_at, description, tags, score, is_favorite`), then any
remaining keys in `sorted()` (alphabetical) order. So a custom column like
`"zeta"` sorts after the defaults, and two custom columns `"b","a"` appear as
`"a","b"`.

#### _format_value(value)

Per-value stringification, in order:

- `None` -> `""` (empty string, not `"None"`)
- `datetime` -> `value.isoformat()`
- `bool` -> `str(value)` (`"True"` / `"False"`)
- `list` / `tuple` -> `"; ".join(str(v) for v in value)` (semicolon-joined)
- `dict` -> `json.dumps(value)` (compact JSON)
- anything else -> `str(value)`

#### _export_csv / _export_json / _export_json_lines

- `_export_csv`: writes a header row (the `col_map`-renamed columns) when
  `include_header` is True, then one row per item where each cell is
  `_format_value(item.get(col, ""))` — a missing key yields `""`. Uses
  `csv.writer` with the given `delimiter`/`quoting` and `lineterminator="\n"`.
- `_export_json`: a JSON **array** of objects, `indent=2`, `ensure_ascii=False`;
  each object maps `col_map.get(col, col)` -> `_format_value(item.get(col, ""))`.
- `_export_json_lines`: one JSON object per line, `ensure_ascii=False`, joined
  with `"\n"` and a trailing `"\n"`.

#### export_to_file(items, filepath, **kwargs)

`content = self.export(items, **kwargs)` then
`with open(filepath, "w", encoding="utf-8") as f: f.write(content)`.

**Contract hole (ARCH-80):** the file is ALWAYS written with the hardcoded
`encoding="utf-8"` (line 199). The `encoding` kwarg a caller passes is
forwarded into `export()` (line 198) where it is silently ignored, so it never
reaches the `open()` call. A caller requesting `encoding="latin-1"` (or any
non-utf-8 encoding) gets a utf-8 file with no error and no signal — the request
is lossy. See the Documented contract hole below.

#### get_stats(items) -> dict

- `if not items: return {"total_items": 0, "columns": 0, "column_names": []}`
- otherwise returns `{"total_items": len(items), "columns": len(columns),
  "column_names": sorted(columns)}` where `columns` is the union of all keys
  across `items`. Note `columns` is the COUNT of distinct columns and
  `column_names` is the sorted list of them; `total_items` is the raw item
  count (NOT the post-filter count — `get_stats` takes no filter/limit).

## Invariants

- `export` never raises for any combination of the documented parameters;
  unrecognized `export_format` degrades to CSV, negative `limit` clamps to 0,
  empty/filtered-empty input returns `""`.
- Output is deterministic: column order is fixed (defaults-first, then
  alphabetical), rows preserve input order unless `sort_key` is given.
- `export_to_file` writes exactly the bytes of `export(...)` encoded as utf-8.
- The exporter is stateless: no instance attributes are set, so concurrent
  calls on one instance do not interfere.

## Persistence

None. `CSVExporter` holds no state and performs no I/O except the single
`open(filepath, "w")` in `export_to_file`. There is no load/save, no temp-file
and rename, no locking.

## Documented contract hole (ARCH-80)

`export_to_file` (lines 191-200) hardcodes `encoding="utf-8"` on the `open()`
call (line 199) and forwards the caller's `encoding` kwarg into `export()`
(line 198), where the parameter (line 80) is accepted but never read. The net
effect: **a caller passing `encoding="latin-1"` (or any non-utf-8 encoding)
receives a utf-8-encoded file with no error, no warning, and no signal** — the
encoding request is silently dropped. The only existing test
(`tests/test_content_export_csv.py::test_export_with_encoding`, line 257)
passes `encoding="utf-8"` (the default), so the lossy non-default path is
un-pinned.

**NOT holes (verified, so future cycles do not re-derive):**
- `export()` returning a `str` and ignoring `encoding` is *by itself* not a
  bug — a string has no encoding; the hole is specifically that
  `export_to_file` advertises (via `**kwargs`) an encoding it then discards.
- The unrecognized-`export_format` fall-through to CSV (line 71) is a
  deliberate degrade, not a raise — it is documented above and is not the
  subject of ARCH-80.
- The negative-`limit` clamp to 0 (lines 91-93) is documented in the
  `export()` docstring and pinned by existing tests; it is not a hole.
- `get_stats` returning a plain `dict` (not `ExportStats`) is a dead-type
  observation, not a behavioral defect; it is noted under `ExportStats` above.
- The sibling `personal_index.content_export/csv_export.py` (line 102) DOES
  honor `self.options.encoding` on its `write_text` — so the hardcoded utf-8 in
  THIS module is a genuine divergence from the sibling's contract, not a
  house-wide convention.
