# TICKET-453

- Module: personal_index/content.py
- Method: ExtractedContent.get_keywords
- Class: (b) doc-drift (docstring under-describes behavior; code is correct)
- Status: OPEN

## Symptom
The `get_keywords` docstring reads:
    """Extract keywords from meta keywords and headings."""
It omits the real behavior the body performs:
  1. starts from `self.meta_keywords` (kept as-is, author-supplied);
  2. for each heading, strips the leading `hN:` level prefix
     (`re.sub(r'^h\d+:\s*', '', heading)`) so the marker is not a keyword;
  3. lowercases and tokenizes to `[a-z0-9]+` words;
  4. filters those heading words through `remove_stopwords`;
  5. returns `list(set(keywords))` — DEDUPLICATED, order NOT guaranteed.

## Evidence
- personal_index/content.py line 31: docstring
- personal_index/content.py lines 32-40: body (prefix strip, tokenize,
  remove_stopwords, list(set(...)))

## Minimal additive fix
Reword the docstring to name the exact behavior (prefix-strip, lowercase +
[a-z0-9]+ tokenize, stopword filter on heading words, meta keywords kept as-is,
deduplicated set, order not guaranteed). Do NOT change the code. Add ONE
pinning test in tests/test_content.py that pins the corrected claim against the
returned object (contains the real words, excludes the stopword and the hN:
markers, and is deduplicated).

Note: renumbered from TICKET-451 -> 452 -> 453 at merge time; parallel runs
claimed 451 (json_export._filter_fields, gh #745) and 452 (archive_old, gh #748).

## Issue
Issue: #744
