# TICKET-446: content_extractor.py ContentExtractor.extract docstring drift

Status: RESOLVED
Issue: #730
Module: personal_index/content_extractor.py
Function: ContentExtractor.extract (line 33)

## Symptom
The `extract` docstring is a blanket one-liner:
    """Extract content from HTML string."""
It does not enumerate the behavior the body actually performs:
- the guard path: empty/falsy `html` returns an empty `ExtractedContent()`
  (all fields at defaults, no parsing).
- the field-by-field extraction: title (og:title preferred over <title>),
  meta_description, meta_keywords (comma-split, stripped, empties dropped),
  author, canonical_url, language.
- the decomposition of script/style/noscript/title tags before body text
  extraction (so the page title is not double-counted in word_count).
- headings (h1-h6, non-empty text), links (text, href) tuples, images
  (alt, src) tuples.
- visible text extraction with whitespace normalization and truncation to
  `max_text_length`.
- `word_count` = len(text.split()).

## Evidence
Line 34: `"""Extract content from HTML string."""`
Body lines 35-68 perform all of the above.

## Minimal additive fix
Reword the docstring to state the EXACT behavior (enumerate the guard path,
the fields extracted, the tag decomposition, the text normalization/truncation,
and word_count). Add ONE pinning test asserting the RETURNED OBJECT fields for
both the normal case and the empty-html guard path. No behavior change.
