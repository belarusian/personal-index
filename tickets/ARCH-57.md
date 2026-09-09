# ARCH-57 — keyword_extractor: `extract_top_n`'s `n` is silently capped by constructor `max_keywords`

Status: OPEN
Component: `personal_index.keyword_extractor.py` — `KeywordExtractor.extract`, `KeywordExtractor.extract_top_n`, `KeywordExtractor.compare_keywords`, module fn `extract_keywords`
Umbrella: ARCH-2 (#983)
Issue: #1182
Docs: `docs/keyword-extractor.md` (Contract Holes)

## Problem
`KeywordExtractor.extract_top_n(text, n)` is documented as "Extract top N keywords as plain strings." The caller expects `len(result) == min(n, number_of_keywords)`. In reality, `extract_top_n` delegates to `self.extract(text)`, which **already truncates** its result to `self.max_keywords` (default 20) before the slice to `n` is applied:

    def extract_top_n(self, text: str, n: int = 10) -> list[str]:
        if n <= 0:
            return []
        keywords = self.extract(text)          # <-- capped to self.max_keywords
        return [kw.text for kw in keywords[:n]]

So whenever `n > self.max_keywords`, the caller silently receives only
`self.max_keywords` items, not `n`. Empirically, `KeywordExtractor().extract_top_n(text, n=50)` on text with 40 distinct keywords returns **20**, not 50. The `n` parameter over-promises; the true cap is an invisible constructor argument.

The same root cause affects `compare_keywords`: it intersects the two `extract` results, each already truncated to `max_keywords`, so a keyword present in both texts but ranking beyond `max_keywords` in either is silently excluded from the comparison.

The module convenience function `extract_keywords(text, max_keywords=10)` avoids the symptom by passing the same value to both the constructor cap and `n`, but the class API itself is misleading.

## Public contract (target)
Make the `n` parameter of `extract_top_n` authoritative, and make the cap explicit.

Options (pick one, document it):
1. **Make `extract` honor a per-call limit** — change `extract` to accept an optional `limit` argument (default `self.max_keywords`) and have `extract_top_n` pass `limit=n`. `extract` still defaults to `self.max_keywords` for callers that use it directly.
2. **Make `extract_top_n` ignore the constructor cap** — have `extract_top_n` call a private `_extract_all` that returns the full un-capped list, then slice to `n`. Keep `self.max_keywords` as the default for `extract` only.
3. **Document the cap and raise** — keep the current implementation but make the contract explicit: `extract_top_n` returns `min(n, self.max_keywords)` and raise `ValueError` if `n > self.max_keywords` (or log a warning). This is the least invasive but still a contract change.

The ARCHITECT prefers option 1 (per-call limit) because it preserves backward compatibility for existing `extract` callers (default remains `max_keywords`) while making `extract_top_n`'s `n` authoritative. The `compare_keywords` method should also be updated to use an un-capped or sufficiently large limit for the intersection, or document the cap explicitly.

## Behavior
- For a `KeywordExtractor(max_keywords=20)` with text containing 40 distinct keywords:
  - `extract_top_n(text, n=50)` returns **50** keywords (or all 40 if fewer exist), not 20.
  - `extract_top_n(text, n=5)` returns 5 keywords.
  - `extract(text)` still returns at most 20 keywords (default cap preserved for direct callers).
- `extract_top_n(text, n=0)` / `n < 0` → `[]` (unchanged guard).
- `extract(text)` with empty text → `[]` (unchanged guard).
- `compare_keywords` should reflect the true intersection of the two texts, not the intersection of two truncated sets (or document the truncation explicitly).

## Guard inputs
- `extract_top_n("", n=10)` → `[]`.
- `extract_top_n(text, n=0)` → `[]`.
- `extract_top_n(text, n=-3)` → `[]`.
- `KeywordExtractor(max_keywords=0).extract(text)` → `[]` (no keywords returned).
- `extract_phrases(text, n=2)` with fewer than 2 tokens → `[]`.

## Acceptance criteria
1. `KeywordExtractor(max_keywords=20).extract_top_n(text_with_40_keywords, n=50)` returns 40 (or 50 if more exist), not 20.
2. `KeywordExtractor(max_keywords=20).extract_top_n(text, n=5)` returns exactly 5 keywords.
3. `KeywordExtractor(max_keywords=20).extract(text)` still returns at most 20 keywords (default cap preserved).
4. `extract_top_n(text, n<=0)` returns `[]` without raising.
5. `compare_keywords` either uses an un-capped extraction for the intersection, or its docstring explicitly states the `max_keywords` cap and the returned dict is the intersection of the two capped sets.

## Pinning tests to add
- `test_extract_top_n_respects_n_over_max_keywords`: `KeywordExtractor(max_keywords=20)` on text with 40 distinct keywords; `extract_top_n(text, n=50)` returns 40 (all keywords), not 20.
- `test_extract_top_n_small_n`: `extract_top_n(text, n=5)` returns exactly 5 items.
- `test_extract_still_capped_by_max_keywords`: `extract(text)` returns at most 20 items.
- `test_extract_top_n_zero_negative_guard`: `extract_top_n(text, n=0)` and `n=-1` return `[]`.

## Docs update (same PR)
`docs/keyword-extractor.md` — Contract Holes section already documents the hole; after the fix, update the section to state the new contract (either `n` is authoritative or the cap is explicit and documented). Remove/adjust the Contract-holes bullet for this hole once merged.
