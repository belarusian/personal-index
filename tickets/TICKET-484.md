# TICKET-484: ContentNormalizer._normalize_title docstring is generic (class-(b) doc-drift)

Status: OPEN
File: personal_index/content_transform/normalizer.py
Method: ContentNormalizer._normalize_title

## Symptom
The docstring is the generic "Normalize title to title case." but the code does
two specific, contract-bearing things:
1. strips surrounding whitespace (str.strip());
2. applies Python's str.title(), which capitalizes the first character of each
   "word" (words split on non-alphanumeric boundaries) and lowercases the
   remaining characters of each word.

## Evidence (lines 64-66)
```python
def _normalize_title(self, title: str) -> str:
    """Normalize title to title case."""
    return title.strip().title()
```

## Actual behavior (verified)
- "  hello world  " -> "Hello World"  (strip + title)
- "HELLO WORLD"     -> "Hello World"  (title lowercases the rest)
- "a b c"           -> "A B C"        (each word capitalized)
- "hello-world"     -> "Hello-World"  (non-alnum boundary splits words)
- ""                -> ""             (empty stays empty)

## Minimal additive fix
- Reword the _normalize_title docstring to state exactly those two behaviors
  (strip, then str.title() with its word-boundary capitalization rule).
- Append a TestNormalizeTitlePinning class to tests/test_content_transform.py
  covering the 5 examples above.

Issue: #819
