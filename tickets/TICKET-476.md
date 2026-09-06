# TICKET-476: count_characters(include_spaces=False) does not strip all whitespace

- File: personal_index/text_utils.py
- Function: count_characters (line ~263)
- Class: (a) behavioral defect
- Symptom: docstring promises include_spaces controls "Whether to count whitespace", but the body only strips 4 specific whitespace chars (" ", "\t", "\n", "\r"). Other whitespace (form feed, vertical tab, non-breaking space) is still counted when include_spaces=False.
- Evidence: count_characters("a\fb", include_spaces=False) == 3 (expected 2); count_characters("a\x0bb", include_spaces=False) == 3 (expected 2); count_characters("a\u00a0b", include_spaces=False) == 3 (expected 2).
- Minimal additive fix: replace the 4 chained .replace() calls with re.sub(r"\s+", "", text).
- Witnessed by a pinning test covering the normal case (space) and the guard path (form feed / vertical tab / nbsp).
- Issue: #805
