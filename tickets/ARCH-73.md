# ARCH-73 — fuzzy_search: `highlight_html` inserts the searched text raw with no HTML entity escaping, so `<`/`>`/`&` in a title pass through into the returned markup (XSS class)

Status: IMPLEMENTED #1426@ef75a9c
Component: `personal_index/fuzzy_search.py` — `FuzzySearcher.highlight_html` (lines 226-239); the raw-insertion half at lines 234-237; the docstring at line 227
Umbrella: ARCH-2 (#983)
Issue: #1409
Docs: `docs/fuzzy_search.md` (Contract Hole 1)

## Problem
`highlight_html(text, indices)` (line 226) builds its output by appending each
character of `text` **raw**:

    for i, char in enumerate(text):
        if i in idx_set:
            result.append(f"<mark>{char}</mark>")
        else:
            result.append(char)          # line 237: raw, unescaped

Neither branch escapes HTML entities. Any `<`, `>`, `&`, `"`, `'` in the
searched text passes straight through into the returned HTML. A text such as
`<script>alert(1)</script>` (or a title containing `&` / `"` / `<`) is emitted
verbatim, so embedding the result in a page yields **unescaped, executable /
malformed markup** — the classic XSS / markup-injection class. The plain
`highlight` path (line 212) is unaffected: it emits ANSI codes, not HTML, so
the HTML path is the single unguarded sink.

The docstring (`"Create HTML-highlighted version of text."`) omits the
escaping behavior entirely, so a caller reading the contract has no reason to
expect the returned string to be safe to embed. This is the same
"advertised safety not actually provided" class as ARCH-39/40/41/42/44/46
(silent unsafe output on a public path), and it is the single most important
hole in this module because the output is user-facing markup.

## Public contract (recommended)
`highlight_html(text: str, indices: list[int]) -> str` must return a string
that is **safe to embed in HTML**: every character of `text` is HTML-entity
escaped (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;`,
`'` → `&#x27;` — i.e. `html.escape` semantics), and the characters at the
positions in `indices` are additionally wrapped in `<mark>...</mark>`.
- Guard path: `not indices` → return the **escaped** text (not the raw text),
  so the no-match path is also safe.
- The plain `highlight` path must remain **unchanged** (ANSI bold, no
  escaping) — the fix is HTML-path-only.
- `search_with_highlight(query, texts, html=True)` inherits the fix
  automatically (it calls `highlight_html`); the `html=False` path is
  unchanged.

## Acceptance criteria
1. `highlight_html` output contains no raw `<`, `>`, `&`, `"`, `'` from the
   input text — every such character is entity-escaped.
2. Matched indices are still wrapped in `<mark>...</mark>` around the
   (escaped) characters, so highlighting is preserved.
3. The `not indices` guard returns the escaped text (safe), not the raw text.
4. The plain `highlight` path is byte-for-byte unchanged (ANSI codes, no
   escaping).
5. `search_with_highlight(..., html=True)` returns escaped, marked output;
   `html=False` is unchanged.

## Pinning tests to add (in `tests/test_fuzzy_search.py`)
- **XSS pin (main behavior):** `highlight_html("<script>alert(1)</script>",
  [0])` (or a title containing `&`/`<`/`>`) returns a string with NO raw
  `<script>` / `&` — assert the returned string contains the escaped forms
  (`&lt;script&gt;`, `&amp;`) and does NOT contain the literal `<script>`.
- **Guard-path pin:** `highlight_html("<b>x</b>", [])` (empty indices) returns
  the escaped text (`&lt;b&gt;x&lt;/b&gt;`), not the raw `<b>x</b>` — one
  returned object pins both the main escaping behavior and the no-match guard.
- **Highlighting-preserved pin:** a normal text with a non-empty index range
  still contains `<mark>` around the matched (escaped) chars.
- **Plain-path-unchanged pin:** `highlight` on the same input still emits
  `\033[1m` ANSI codes and no HTML entities (guards against over-escaping the
  plain path).

## Docs
`docs/fuzzy_search.md` (new page, this PR) documents the full public API and
records this as Contract Hole 1 with the recommended escaping contract.
