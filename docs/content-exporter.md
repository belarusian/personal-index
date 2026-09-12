# content-exporter — Exact Contract

Module: `personal_index/content_exporter.py` (184 lines, stdlib-only imports:
`html`, `json`, `datetime`, `typing`, `xml.sax.saxutils`).

Content export to multiple formats. One public type: `ContentExporter` (the
engine: `export`, `export_to_file`, `detect_format`). It renders a list of
content items (each a `dict[str, Any]`) into one of four string formats —
`html`, `json`, `markdown`, `rss` — selected by the `fmt` argument. There is
**no** persistence layer of its own: `export` returns a `str` and
`export_to_file` writes that string to a caller-supplied path. The item schema
is duck-typed: every renderer reads the keys `title`, `description`, `link`,
`date`, `tags` (and `id` for RSS) via `item.get(...)` with a default, so a
missing key never raises — it degrades to the format's default.

## Public API

### ContentExporter

Plain class (not a dataclass). Class attribute:

- `SUPPORTED_FORMATS = ("html", "json", "markdown", "rss")` — the four
  normalized format tokens `export` accepts.

`__init__(self, title: str = "Personal Index", base_url: str = "http://localhost:8000") -> None`:

- `self.title = title` — used as the document title (HTML `<title>`/`<h1>`,
  Markdown H1, RSS `<title>`/`<description>`).
- `self.base_url = base_url.rstrip("/")` — trailing slashes are stripped once
  at construction; used as the RSS channel `<link>` and as the fallback for an
  item's `link`/`guid` in RSS.

`export(self, items: list[dict[str, Any]], fmt: str) -> str`:

- Normalizes the format with `fmt = fmt.lower().strip()` before use, so padded
  or mixed-case tokens (`"JSON "`, `" Html"`) are accepted.
- If the normalized `fmt` is not in `SUPPORTED_FORMATS`, raises
  `ValueError(f"Unsupported format: {fmt}. Supported: {self.SUPPORTED_FORMATS}")`
  **before any handler runs** (no partial output, no side effect).
- Otherwise dispatches to the private `_export_{fmt}` handler via
  `getattr(self, f"_export_{fmt}")` and returns its `str`. Because `fmt` is
  validated against `SUPPORTED_FORMATS` first, the `getattr` can only ever
  resolve to one of the four known handlers — it is not an arbitrary-attribute
  access path.
- Empty input is well-defined: `export([], fmt)` returns a valid empty
  document for each format (HTML shell with no `<article>`, JSON `"[]"`,
  Markdown with only the H1, RSS channel with no `<item>`). No error is raised
  for an empty list.
- **Per-format escaping contract** (stated so a caller knows, without reading
  the source, which characters each format sanitizes and which it does not):
  - **HTML**: every user-supplied field (title, description, tags, link, and
    the document title) is escaped with `html.escape` (escapes `& < > " '`).
  - **RSS**: title, description, link, and guid are escaped with
    `xml.sax.saxutils.escape` (escapes only `& < >` — **not** the quotes
    `"`/`'`).
  - **Markdown**: title, link, description, tags, and the document H1 title are
    escaped for well-formed Markdown — backslash, `[`, `]`, `(`, `)` are
    escaped, newlines are collapsed to spaces, and link-target spaces are
    percent-encoded (`%20`) — so the output is well-formed for arbitrary input
    (no broken link syntax, no stray heading or list).
  - **JSON**: fields are serialized verbatim by `json.dumps` (no escaping
    beyond JSON's own string rules).

`export_to_file(self, items, fmt, filepath) -> str`:

- Calls `self.export(items, fmt)` (so the same format validation and
  `ValueError` apply), writes the returned string to `filepath` with
  `open(filepath, "w", encoding="utf-8")`, and returns `filepath`.
- Note: the three parameters are **untyped** (no annotations) in the signature,
  unlike `export`. A `ValueError` from `export` propagates before any file is
  opened; a filesystem error (e.g. bad path) propagates from `open`.

`detect_format(filepath) -> str | None` (staticmethod):

- `ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""` — the
  last dot-separated segment, lowercased; `""` when the path has no dot.
- Maps `{"html": "html", "htm": "html", "json": "json", "md": "markdown",
  "markdown": "markdown", "rss": "rss", "xml": "rss"}` and returns
  `mapping.get(ext)` — i.e. the normalized format token, or **`None`** when the
  extension is absent or not in the mapping (e.g. `"txt"`, `"csv"`, or a path
  with no dot). The caller must handle the `None` return; `detect_format`
  never raises.

### Private renderers (referenced for exact semantics)

- `_export_json(items) -> str`: `json.dumps(items, indent=2, default=str)` —
  `default=str` stringifies any non-JSON-serializable value (e.g. a `datetime`)
  rather than raising.
- `_export_html(items) -> str` → `_render_html`: emits `<!DOCTYPE html>`,
  `<html lang="en">`, a `<head>` with `<title>`/`<meta charset="utf-8">`/inline
  `<style>`, a `<body>` with an `<h1>`, one `<article>` per item
  (`_html_item`), then `</body></html>`; parts joined with `"\n"`.
- `_html_item(item) -> str`: title/description/tags are `html.escape`-ed; the
  `link` is `html.escape`-d into `href="..."` only when truthy (otherwise no
  `href` attribute); `date` goes through `_format_date`; missing keys degrade
  to `"Untitled"` / `""` / `[]`.
- `_export_markdown(items) -> str` → `_render_markdown`: `lines = [f"# {self.title}", ""]`
  then one `_md_item` block per item; joined with `"\n"`.
- `_md_item(item) -> str`: heading is `f"## [{title}]({link})"` when `link` is
  truthy else `f"## {title}"`; `description` is appended when truthy; a
  `📅 <date>` / `🏷️ <tags>` meta line is appended only for the present parts.
  **All fields are escaped for well-formed Markdown** (title, link,
  description, tags, and the H1 `self.title`): backslash, `[`, `]`, `(`, `)`
  are escaped, newlines are collapsed to spaces, and link-target spaces are
  percent-encoded (`%20`). See the per-format escaping contract on `export`
  above.
- `_md_escape(text) -> str`: escapes backslash, `[`, `]`, `(`, `)` and
  collapses newlines to spaces (inline-field escaping).
- `_md_link_target(link) -> str`: collapses newlines, escapes backslash and
  parentheses, and percent-encodes spaces (`%20`) so the `(...)` target syntax
  is never broken.
- `_export_rss(items) -> str` → `_render_rss`: emits the XML declaration,
  `<rss version="2.0">`, a `<channel>` with `xml_escape`-d `<title>`/`<link>`
  (base_url)/`<description>` and a `<lastBuildDate>` stamped from
  `datetime.now(timezone.utc)`, one `<item>` per item (`_rss_item`), then
  `</channel></rss>`; joined with `"\n"`.
- `_rss_item(item) -> str`: title/description are `xml_escape`-d; `link` is
  `xml_escape(item.get("link", self.base_url))` (falls back to base_url);
  `guid` is `xml_escape(item.get("id", link))` (falls back to the already-
  resolved link, so it is never empty); `date` goes through `_format_rss_date`.
- `_format_date(date_val) -> str`: `None` → `""`; a `datetime` →
  `strftime("%Y-%m-%d")`; anything else → `str(date_val)` (a caller-supplied
  string is preserved verbatim).
- `_format_rss_date(date_val) -> str`: `None` → `""`; a `datetime` →
  `strftime("%a, %d %b %Y %H:%M:%S +0000")`; anything else → `str(date_val)`.

## Contract Holes

### Primary hole: per-format escaping is inconsistent, and Markdown performs no escaping (ARCH-48)

The public `export` contract states only that a format is normalized and
validated; it states **no per-format escaping guarantee**, and the three
escaping-sensitive formats do not agree:

- **HTML** escapes every user-supplied field with `html.escape` (which escapes
  `& < > " '`).
- **RSS** escapes with `xml_escape` (which escapes only `& < >` — **not** the
  quotes `"`/`'`).
- **Markdown** escapes **nothing**: `title`, `link`, `description`, `tags`, and
  even the document H1 `self.title` are interpolated verbatim into the output.

The concrete underspecified semantic is the **Markdown path**: a content item
whose `title`, `link`, or `description` contains Markdown-significant characters
silently produces malformed or structurally broken Markdown with no error and no
signal. For example:

- A `title` containing `](` or `)` breaks the `## [{title}]({link})` heading
  link syntax (an unbalanced `](` yields a literal, non-link heading; a stray
  `)` truncates the link target).
- A `link` containing a space or `)` breaks the `({link})` target.
- A `description` containing a newline, a `#` at line start, or a `|` is
  reinterpreted by any Markdown renderer as a new heading / table cell / list,
  changing the document structure.
- A `self.title` containing `#` or a newline breaks the top-level H1.

Because `export`'s docstring and this page make no escaping promise, an
implementer or caller cannot tell from the contract that Markdown output is
unescaped while HTML/RSS are (partially) escaped — the same input yields
differently-sanitized output depending on `fmt`, and the Markdown case is the
only one with zero sanitization. The fix is to make the per-format escaping
contract explicit (either escape Markdown-significant characters in `_md_item`
and the H1, or document that Markdown output is unescaped and the caller must
pre-sanitize), and to state the escaping guarantee for each format in the
`export` contract.

### Secondary notes (not ticketed)

- `export_to_file`'s three parameters are untyped, unlike `export`; a
  `ValueError` from `export` propagates before the file is opened, and a
  filesystem error propagates from `open`.
- `detect_format` returns `None` (not a format token) for an absent or
  unrecognized extension, and maps `xml` → `rss`; the caller must handle `None`.
- JSON uses `default=str`, so non-serializable values (e.g. a `datetime` in an
  item) are stringified rather than raising.
- Empty input is well-defined (valid empty document per format, no error) —
  this is a defined behavior, not a hole.
