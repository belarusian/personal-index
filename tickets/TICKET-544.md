# TICKET-544: content_scoring._score_freshness placeholder docstring

**Status:** RESOLVED (merged on main 29e7a98, issue #962 closed)
**File:** personal_index/content_scoring.py
**Symptom:** `_score_freshness` (line 290) carries only the placeholder
docstring "Score based on content freshness." while its siblings
`_score_authority` and `score_page` carry exact contracts. The body has
non-obvious behavior the docstring does not state: a guard path
(`last_crawled is None` -> 0.5), a naive-datetime normalization, a
"never" frequency short-circuit (-> 1.0), and a linear decay
`1.0 - (age_hours/expected) * 0.5` clamped to [0,1] and rounded to 4
places, where `expected` comes from a fixed frequency->hours table
(hourly 1, daily 24, weekly 168, monthly 720, yearly 8760, never inf)
defaulting to 720 for unknown frequencies. The `updated_at` parameter is
unused.

**Evidence:** line 297 `"""Score based on content freshness."""` vs the
exact-contract docstrings at lines 279-284 (`_score_authority`) and
328-354 (`score_page`).

**Minimal additive fix:** reword the docstring to state the exact
conditional (guard path, naive-datetime handling, "never" short-circuit,
decay formula, frequency table + default, unused `updated_at`), and add
ONE pinning test calling `_score_freshness` directly that pins the
`last_crawled is None` guard path (0.5), the "never" path (1.0), and the
decay formula against the returned float.

**Issue:** #962
