# ARCH-48: content-exporter — per-format escaping is inconsistent; Markdown escapes nothing

Status: IMPLEMENTED #1311@a93016c (cycle 252)
Component: `personal_index/content_exporter.py`
Issue: #1143
Refs: ARCH-2 (#983 umbrella)

## Symptom

`ContentExporter.export` states only that the format is normalized
(`fmt.lower().strip()`) and validated against `SUPPORTED_FORMATS`; it states
**no per-format escaping guarantee**. The three escaping-sensitive formats do
not agree on what they sanitize:

- **HTML** (`_html_item`) escapes every user-supplied field with `html.escape`
  (escapes `& < > " '`).
- **RSS** (`_rss_item`) escapes with `xml.sax.saxutils.escape` (escapes only
  `& < >` — **not** the quotes `"`/`'`).
- **Markdown** (`_md_item` and the H1 in `_render_markdown`) escapes
  **nothing**: `title`, `link`, `description`, `tags`, and even the document
  H1 `self.title` are interpolated verbatim into the output.

The concrete underspecified semantic is the **Markdown path**: a content item
whose `title`, `link`, or `description` contains Markdown-significant
characters silently produces malformed or structurally broken Markdown with no
error and no signal. Because the `export` contract makes no escaping promise,
an implementer or caller cannot tell from the contract that Markdown output is
unescaped while HTML/RSS are (partially) escaped — the same input yields
differently-sanitized output depending on `fmt`, and Markdown is the only
format with zero sanitization. This is the single most important hole: it is
the one format where the output is silently wrong for ordinary input, and the
contract gives no way to know.

## Public contract (the fix must preserve the happy path)

- All public methods keep their current signatures and behavior:
  `export(items, fmt)` (normalize + validate + dispatch, `ValueError` before
  any handler runs, empty input → valid empty document), `export_to_file`
  (delegates to `export`, writes utf-8, returns the path), `detect_format`
  (extension → normalized token or `None`, never raises).
- The per-format escaping contract must be made explicit (pick one and state it
  in the `ContentExporter.export` docstring + `docs/content-exporter.md`):
  - **Option A (escape Markdown):** escape Markdown-significant characters in
    `_md_item` (title, link, description, tags) and in the H1 `self.title` in
    `_render_markdown` so the output is well-formed Markdown for arbitrary
    input (e.g. escape `[`, `]`, `(`, `)`, backslash, and strip/neutralize
    newlines in inline fields). State in the contract that HTML uses
    `html.escape`, RSS uses `xml_escape`, and Markdown escapes
    Markdown-significant characters.
  - **Option B (document the unescaped contract):** if Markdown is
    intentionally left unescaped, state it explicitly in the `export`
    docstring and `docs/content-exporter.md` — "Markdown output is NOT
    escaped; the caller must pre-sanitize `title`/`link`/`description`/`tags`
    and the exporter title before export" — and state the HTML/RSS escaping
    guarantees alongside it, so a caller is not misled into treating all
    formats as equally sanitized.
- Whichever option is chosen, the postcondition must hold and be stated: a
  caller reading the `export` docstring must know, without reading the source,
  which characters each format sanitizes and which it does not.

## Acceptance criteria

1. The happy path is unchanged: `export`/`export_to_file`/`detect_format`
   behave exactly as documented in `docs/content-exporter.md` for the four
   supported formats, including the `ValueError` on an unsupported format and
   the valid-empty-document behavior for `export([], fmt)`.
2. The per-format escaping contract is stated in the `ContentExporter.export`
   docstring and in `docs/content-exporter.md` (Option A: Markdown output is
   escaped and well-formed for arbitrary input; Option B: Markdown output is
   unescaped and the caller must pre-sanitize). The HTML (`html.escape`) and
   RSS (`xml_escape`) guarantees are stated in the same contract.
3. If Option A: a Markdown item whose `title`/`link`/`description` contains
   `](`, `)`, a space in the link, or a newline renders as well-formed Markdown
   (the link syntax is not broken and no stray heading/list is introduced).
4. If Option B: the docstring and the docs page both state that Markdown is
   unescaped, and no caller-facing API implies Markdown is sanitized.

## Pinning tests to add (tests/test_content_exporter.py)

- `test_export_markdown_normal_item` (happy path) — a well-formed item
  (title, link, description, tags, date) exports to Markdown with the expected
  `## [{title}]({link})` heading, the description line, and the `📅`/`🏷️` meta
  line; pins the current happy-path shape so the escaping fix does not change
  clean input.
- `test_export_markdown_special_chars` (the contract hole) — an item whose
  `title` contains `](` and whose `link` contains a space (and a `description`
  containing a newline) exports to Markdown that is well-formed under Option A
  (link syntax intact, no stray heading) OR, under Option B, the documented
  unescaped contract is asserted (the raw characters appear verbatim and the
  docstring states the caller must pre-sanitize). This single test pins the
  whole contract hole.
- `test_export_escaping_per_format` (guard path) — the same special-character
  input exported as `html` and `rss` shows the differing sanitization
  (`html.escape` vs `xml_escape`) that the contract now states, so one test
  pins both the main behavior (Markdown) and the guard path (the other two
  formats' guarantees).

## Docs update (same PR)

`docs/content-exporter.md` "Contract Holes" section (already authored in this
PR) names this as the primary hole; the implementer must update the
`ContentExporter.export` entry in the "Public API" section to state the chosen
per-format escaping contract once implemented.
