# TICKET-349: extract_readability_score docstring over-promises "readability"

- **File:** personal_index/content_extractor.py
- **Line:** 149 (docstring of `extract_readability_score`)
- **Symptom:** Docstring says "Calculate a readability score for extracted content."
  The code does NOT compute linguistic readability (sentence length, word
  complexity, Flesch-Kincaid, etc.). It computes a **content richness** score
  from three components:
    1. Length: min(word_count / 500, 0.4)
    2. Headings: min(len(headings) * 0.1, 0.3)
    3. Meta description: 0.3 if present, else 0
  Returns 0.0 when text is empty or word_count < 50. Capped at 1.0.
- **Evidence:** Line 149 docstring vs. lines 150-163 body.
- **Fix:** Reword docstring to enumerate the three components and the 50-word
  threshold. Add one behavior test that calls `extract_readability_score` with
  a known ExtractedContent and asserts the exact returned float, pinning the
  corrected claim.
- **Status:** RESOLVED (merged to main c5bd700, gh #536 closed)
