# export_markdown — Exact Contract

Module: `personal_index/export_markdown.py` (336 lines, stdlib-only imports:
`html`, `logging`, `dataclasses`, `datetime`, `enum`, `typing`).

Content export to three string formats. Two public types: `ExportConfig` (a
5-field `@dataclass` with `__post_init__` validation) and `MarkdownExporter`
(the engine: `export` dispatching to `_export_markdown` / `_export_html` /
`_export_plain_text`, plus the private `_sort_items` / `_group_items` /
`_render_md_item` / `_truncate` helpers). Three module-level convenience
functions: `export_to_md`, `save_markdown`, `export_markdown`. `export`
returns a `str` (empty string on empty input); it never raises on a
well-formed item list.

> **Disambiguation (near-name collision):** This page documents
> `personal_index.export_markdown` (module `personal_index/export_markdown.py`,
> public types `MarkdownExporter` / `ExportConfig`, format enum
> `ExportFormat` = markdown/html/plain_text). It is **DIFFERENT** from:
> - `personal_index.export` (see [export.md](export.md), types `Exporter` / `ExportResult`, six file formats)
> - `personal_index.content_exporter` (see [content-exporter.md](content-exporter.md), class `ContentExporter`)
> - `personal_index.content_export_csv` (see [content-export-csv.md](content-export-csv.md), class `CSVExporter`)
> - `personal_index.bookmark_export` (see [bookmark_export.md](bookmark_export.md), class `BookmarkExporter`)
> - the `personal_index/content_export/` subpackage (`csv_export` / `json_export` / `markdown_export`)
>
> Tests import from this module: `from personal_index.export_markdown import
> MarkdownExporter, ExportConfig` (see `tests/test_export_markdown.py`,
> `tests/test_ticket44_builtin_shadowing.py`,
> `tests/deep/test_export_markdown_adversarial.py`).

## Public API

### ExportFormat (str Enum, line 15)

Three members: `MARKDOWN = "markdown"`, `HTML = "html"`,
`PLAIN_TEXT = "plain_text"`.

### ExportConfig (dataclass, line 24)

Five fields, all defaulted:

- `include_metadata: bool = True` — emit the `**Published:**` date line.
- `include_tags: bool = True` — emit the `**Tags:**` line.
- `include_summary: bool = False` — see the Documented Contract Hole: the
  default keeps the **full** content; `True` **replaces** the content with a
  200-char truncation.
- `sort_by: str = "date"` — one of `{"date", "title", "priority", "relevance"}`.
- `group_by: str | None = None` — one of `{"tags", "date", "category", None}`.

`__post_init__` (line 34) raises `ValueError` on an invalid `sort_by`
(`"Invalid sort_by '<v>'. Must be one of: {...}"`) or an invalid `group_by`
(`"Invalid group_by '<v>'. Must be one of: {...}"`). The valid sets are the
`ClassVar`s `_VALID_SORT` and `_VALID_GROUP`.

### MarkdownExporter (class, line 47)

`__init__(self, config: ExportConfig | None = None) -> None`:
`self.config = config or ExportConfig()` — the injected config, or a fresh
default when none is supplied.

`export(self, items: list[dict[str, Any]], export_format: ExportFormat | None = None) -> str`:

- Empty `items` (`[]`) returns `""` immediately (guard, line 78).
- `export_format` defaults to `ExportFormat.MARKDOWN` when `None`
  (`use_format = export_format or ExportFormat.MARKDOWN`, line 82).
- Sorts via `_sort_items`, then dispatches on `use_format` to
  `_export_markdown` / `_export_html` / `_export_plain_text`. The final
  `return self._export_markdown(sorted_items)` (line 94) is unreachable for a
  valid `ExportFormat` (all three members are handled above) — a defensive
  fallback.

`_sort_items` (line 96): `date` sorts by
`published_date or created_at` descending; `title` by lowercased title
ascending; `priority` by `priority_score` descending; `relevance` by
`relevance_score` descending. Missing fields default to `""` / `0` and never
raise.

`_group_items` (line 120): `group_by=None` → `{"all": items}`. `tags` → one
group per lowercased tag, items with no tags go to `"untagged"`. `date` → one
group per `YYYY-MM` (via `datetime.fromisoformat`), unparseable/missing dates
go to `"unknown"`. `category` → one group per `category` (missing →
`"uncategorized"`).

`_truncate(self, text: str, max_length: int) -> str` (line 251): returns
`text` unchanged when `len(text) <= max_length`; otherwise
`text[:max_length].rsplit(" ", 1)[0] + "..."` — truncates to `max_length`
chars, backs off to the last space (word boundary), appends `...`.

### Module-level convenience functions

- `export_to_md(data: dict) -> str` (line 266): wraps a single `dict` in a
  list (or passes a list through), returns `MarkdownExporter().export(items)`.
- `save_markdown(data: dict, filepath: str) -> bool` (line 285): exports to
  markdown, `mkdir(parents=True, exist_ok=True)` on the parent, writes the
  file, returns `True`; on any exception logs and returns `False` (never
  raises).
- `export_markdown(results, tag_store=None) -> str` (line 311): renders a list
  of `SearchResult` objects (attribute access: `.title` / `.url` /
  `.relevance_score` / `.snippet`) as a `# Search Results` markdown doc; empty
  `results` → `"# No Results\n\nNo content found matching your query."`.

## Invariants

- `export` **never raises** on a well-formed item list: missing keys default
  (`title` → `""` via `.get("title", "Untitled")` when the key is *absent*,
  `url`/`content`/`date` → `""`, `tags` → `[]`), and an empty list returns
  `""`.
- `export` does **not mutate** the input items (sort/group operate on copies
  of the list, not the dicts).
- HTML output escapes `title`, `url`, `date`, and each `tag` exactly once via
  `html.escape`; `content` is escaped exactly once (the QA-33 double-escape is
  fixed). Markdown and plain-text output do **not** escape (raw interpolation).
- `include_metadata` / `include_tags` gate their respective lines; when
  `False` the line is omitted entirely.
- `save_markdown` swallows all exceptions and returns `False` (it never
  raises); `export_to_md` / `export_markdown` do not catch.

## Persistence

`save_markdown` writes the exported markdown to the caller-supplied `filepath`
(UTF-8, `Path.write_text`), creating parent directories. The module is a
read-only consumer of the item dicts; it does not persist or mutate any
backing store.

## Documented Contract Hole

**`include_summary` is inverted: the default keeps the FULL content and
`True` makes the export LOSSY (replaces content with a 200-char truncation).**
All three renderers use the same expression
(`self._truncate(content, 200) if self.config.include_summary else content`)
at line 173 (markdown), line 207 (HTML), and line 243 (plain text). The flag
name `include_summary` implies "add a summary", but the code uses it as a
*replace* flag: with the default `include_summary=False` the **full** content
is emitted, and setting `include_summary=True` **drops** the content beyond
200 chars (word-boundary truncation + `...`). A caller who reads the flag
name and sets `include_summary=True` expecting a summary *in addition to* the
content instead gets a lossy export that silently discards most of the
content. The existing deep test
`test_truncate_summary_mode_applies_to_content` only asserts `"..." in out`
for the `True` case — it does **not** pin that the full content is dropped,
nor that the default (`False`) keeps the full content, so the inversion is
unpinned. See ARCH-82 for the precise contract.

**Adjacent behaviors that are NOT holes** (do not re-ticket):
- HTML `content` is escaped exactly once (QA-33 double-escape fixed) — pinned
  by `test_html_content_single_escaped_round_trips`.
- `_truncate` mechanics (short unchanged, exact-length unchanged, long adds
  `...`, word-boundary backoff) — pinned by `test_truncate_short_unchanged`,
  `test_truncate_exact_length_unchanged`, `test_truncate_long_adds_ellipsis`,
  `test_truncate_breaks_at_word_boundary`.
- `ExportConfig` validation (invalid `sort_by` / `group_by` raise
  `ValueError`) — pinned by `test_config_invalid_sort_by_raises` /
  `test_config_invalid_group_by_raises`.
- Empty-list guard (`export([]) == ""` for all three formats) — pinned by
  `test_export_empty_list_returns_empty_string` and the per-format empty tests.
- `export` does not mutate input items — pinned by
  `test_export_does_not_mutate_items`.
