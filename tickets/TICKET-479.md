# TICKET-479: count_characters(include_spaces=False) does not strip all whitespace

- File: personal_index/text_utils.py
- Method: count_characters
- Symptom (class-a behavioral): the docstring promises `include_spaces`
  controls whether to count whitespace, but the body only strips 4 specific
  whitespace chars (space, tab, newline, carriage return) via chained
  `.replace()` calls. Form feed (\x0c), vertical tab (\x0b), and other
  whitespace (e.g. non-breaking space) are still counted when
  include_spaces=False.
- Evidence line: `return len(text.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", ""))`
  (line ~277). Verified: count_characters('a\x0cb', include_spaces=False) == 3
  (should be 2); count_characters('a\x0bb', include_spaces=False) == 3 (should be 2).
- Minimal additive fix: replace the chained .replace() with `re.sub(r"\s+", "", text)`
  so every whitespace char is stripped when include_spaces=False. `re` is already
  imported at module top.
- Pinning test: add a test that includes form feed and vertical tab alongside a
  normal space, asserting the stripped count (fails pre-fix, passes post-fix).
- Status: OPEN
- Issue: #805
