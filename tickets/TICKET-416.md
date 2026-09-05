# TICKET-416: content_categorizer.ContentCategorizer.categorize docstring over-promise

- **File:** personal_index/content_categorizer.py
- **Function:** `ContentCategorizer.categorize`
- **Symptom (class b - doc drift):** docstring is the blanket one-liner
  `"""Categorize content into topics."""`. It does not enumerate the guard
  path, the return fields, or the side-effect-free scoring pipeline the body
  actually performs.
- **Minimal additive fix:**
  1. Reword the docstring to state the EXACT behavior:
     - GUARD PATH: if `text`, `title` and `meta_description` are all falsy,
       return `CategorizationResult(primary_topic="unknown", topics=[],
       confidence=0.0, reasons=["no content provided"])` (text_length and
       keyword_count stay at their dataclass defaults 0).
     - NORMAL PATH: tokenize text/title/meta (lowercase, stopword-removed),
       extract URL hints, score every topic, drop scores below `min_score`,
       cap the list at `max_topics`, set `primary_topic` to the top topic's
       name (or `"uncategorized"` when no topic clears the threshold),
       `confidence` to the top score rounded to 4, `reasons` to the built
       human-readable list, `text_length` to `len(text.split())`, and
       `keyword_count` to the number of distinct text tokens.
  2. Add ONE pinning test asserting the RETURNED OBJECT fields for BOTH the
     guard path and the normal path.
  3. Rework the test_exception_handling urlparse pin from a hardcoded line
     range to AST `_method_line_span` (the added docstring lines shifted the
     except block).
- **Status:** RESOLVED (PR #671, merged 786d009)
- **Issue:** #669
- **Note:** renumbered from TICKET-415 (owned by content_pin.pin, PR #670).
