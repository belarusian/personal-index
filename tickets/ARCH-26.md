# ARCH-26: content_extractor — extract_readability_score ignores the word_count field (docstring says "word_count < 50" but the body re-splits content.text)

- **Status:** CLAIMED 2026-09-12
- **Component:** `personal_index/content_extractor.py` (`ContentExtractor.extract_readability_score`).
- **Issue:** #1071

## Symptom
`ContentExtractor.extract_readability_score(content)` is documented as
"Returns 0.0 if text is empty or `word_count < 50`", but the body never reads
`content.word_count`. It recomputes the word count from the text:

```python
if not content.text:
    return 0.0
words = content.text.split()
if len(words) < 50:
    return 0.0
score = 0.0
score += min(len(words) / 500, 0.4)   # length component from re-split text
...
```

So the guard and the length component are both derived from
`content.text.split()`, not from the `word_count` field the docstring names.
For an `ExtractedContent` built by `extract()` the two agree, but for any
hand-built object (or one whose `word_count` was set independently) the
documented `word_count` field is silently ignored — a consumer that sets
`word_count` and leaves `text` short (or vice-versa) gets a score that does
not match the documented contract.

This is the same shape as the recurring "docstring names a field the body
recomputes" drift class, and it is the single most important hole on the new
`docs/content-extractor.md` spec page.

## Evidence
- `personal_index/content_extractor.py:161` — `extract_readability_score` docstring
  — "Returns 0.0 if text is empty or word_count < 50."
- `personal_index/content_extractor.py:168` — `words = content.text.split()`.
- `personal_index/content_extractor.py:169` — `if len(words) < 50: return 0.0`
  (guard uses re-split text, not `content.word_count`).
- `personal_index/content_extractor.py:174` — `score += min(len(words) / 500,
  0.4)` (length component uses re-split text, not `content.word_count`).
- `personal_index/content_extractor.py:24` — `ExtractedContent.word_count:
  int = 0` is a public field that the score never reads.
- `tests/test_content_extractor.py:225-253` — the readability tests build
  `ExtractedContent(text=..., ...)` and never set `word_count`, so the
  divergence is not pinned.

## Public contract (target state)
`extract_readability_score` MUST derive its word count from a single,
documented source. Two acceptable resolutions — the implementer picks ONE and
the docstring MUST state it:
- **(a) Use the field:** guard on `content.word_count < 50` and compute the
  length component from `content.word_count` (i.e. `min(content.word_count /
  500, 0.4)`), so the score is a pure function of the documented
  `ExtractedContent` fields. The docstring keeps "word_count < 50".
- **(b) Use the text:** keep the body as-is (re-split `content.text`) and
  reword the docstring to "Returns 0.0 if `text` is empty or
  `len(text.split()) < 50`" so the contract names the source it actually
  reads.

Whichever is chosen, the guard path (empty text → 0.0) and the short-text
guard (< 50 words → 0.0) MUST be witnessed by a pinning test that sets the
field the docstring names, so the returned float pins the documented source.
Behavior that MUST be preserved: the three-component formula
(`min(words/500, 0.4) + min(len(headings)*0.1, 0.3) + 0.3 if
meta_description`, capped at 1.0) and the empty-text → 0.0 guard.

## Acceptance criteria
1. The docstring of `extract_readability_score` names the SAME source the body
   reads (either `word_count` or `len(text.split())`) — no field named in the
   docstring is ignored by the body.
2. A hand-built `ExtractedContent` whose `word_count` and `len(text.split())`
   disagree yields the score the docstring promises (i.e. the test in the
   pinning section passes).
3. The empty-text guard still returns `0.0` and the short-text guard (< 50
   words) still returns `0.0`.
4. Existing `tests/test_content_extractor.py` readability assertions
   (`test_readability_score_empty`, `_short`, `_good`, `_exact_components`)
   stay green.

## Pinning tests to add
- `test_readability_score_uses_documented_word_source` (the divergence pin):
  build an `ExtractedContent` where `word_count` and `len(text.split())`
  disagree — e.g. `ExtractedContent(text=" ".join(["w"] * 200),
  word_count=10, headings=["h"], meta_description="d")` — and assert the
  returned float matches the docstring-named source (under resolution (a):
  `word_count=10 < 50` → `0.0`; under resolution (b): `len(text.split())=200`
  → `min(200/500,0.4)+min(1*0.1,0.3)+0.3 == 0.8`). This one returned object
  pins both the guard path and the length component against the documented
  source.
- `test_readability_score_short_guard` (guard path): an `ExtractedContent`
  with < 50 words in the documented source → assert `0.0`.

## Docs
`docs/content-extractor.md` (this cycle) documents the hole as contract hole 1
and notes the pre-truncation `word_count` / post-truncation text mismatch as
contract hole 2. The implementer keeps the page true when fixing: mark
contract hole 1 RESOLVED, state which resolution (a)/(b) was taken in the
`extract_readability_score` section, and reconcile contract hole 2 (either
fix `word_count` to be computed post-truncation or document the mismatch).

## References
- Part of the ARCH-2 (#983) docs-coverage umbrella (advances one bounded page
  per cycle; `content_extractor` is this cycle's page).
- Same drift shape as the recurring "docstring names a field the body
  recomputes" class; distinct from the negative-slice-truncation class
  (ARCH-17, #1049).
