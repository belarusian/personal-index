# TICKET-343: truncate_text docstring over-promises "without breaking words"

**File:** personal_index/text_utils.py
**Symptom:** `truncate_text` docstring says "Truncate text to a maximum length
without breaking words." — implying the cut always lands on a word boundary.
But the body only breaks at a word boundary when a space exists AFTER 60% of
`max_length` (`if last_space > max_length * 0.6`). When the truncated window
has no space past that 60% mark (e.g. a long unbroken token in the tail), it
keeps `text[:max_length]` and cuts MID-WORD. The "without breaking words"
claim is false for that case.
**Evidence:** Docstring line ~51: "Truncate text to a maximum length without
breaking words." vs body: `truncated = text[:max_length]` then
`last_space = truncated.rfind(" ")` / `if last_space > max_length * 0.6:
truncated = truncated[:last_space]`. Repro: `truncate_text('hello world ' +
'x'*200, max_length=200)` returns a 203-char string ending in a mid-word
`x`-run + "..." (the only space is at index 11, which is not > 120, so no
word-break is applied).
**Fix:** Reword the docstring to state the actual behavior: the cut is made at
a word boundary only when a space exists in the latter part of the window
(after 60% of max_length); otherwise the text is cut at exactly max_length and
may break a word. (doc-only, no behavior change.)
Add one behavior test pinning the corrected claim: a long unbroken tail token
is cut mid-word (result ends in the token's characters + suffix, not on a
space), documenting that "without breaking words" is not guaranteed.
**Status:** OPEN
**Issue:** #524
