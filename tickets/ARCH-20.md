Status: CLAIMED 2026-09-06
Kind: ARCH
Author: architect (cycle 182)
Issue: #1056

# ARCH-20: scraper — dead `remove_scripts` flag + `word_count`/truncation inconsistency

## Component
`personal_index/scraper.py` (home: `docs/content-scraper.md`).
Two related contract holes in the HTML scraper.

## Symptom

1. **Dead `remove_scripts` flag.** `ScraperConfig.remove_scripts` (default
   `True`) is stored on the dataclass but never read anywhere in the module.
   Script/style/noscript removal is driven entirely by `blocked_tags`
   (default `["script", "style", "noscript"]`) in `_clean_page`. A caller who
   sets `remove_scripts=False` expecting scripts to be kept gets no effect —
   the `blocked_tags` default still decomposes them. The flag is a silent
   no-op, so its presence misleads readers into thinking it controls script
   removal.

2. **`word_count` inconsistent after truncation.** In `scrape`, `word_count`
   is computed from `raw_text` (step: `result.word_count =
   len(result.raw_text.split())`) *before* the `max_content_length`
   truncation (`result.raw_text = result.raw_text[: max_content_length]`).
   When `raw_text` is truncated, `word_count` still reflects the
   pre-truncation text, so `word_count != len(result.raw_text.split())`. A
   caller who relies on `word_count` to describe the returned `raw_text` is
   wrong for pages longer than `max_content_length`. The docstring does not
   state this ordering.

## Public contract (the fix)

### Hole 1 — remove the dead `remove_scripts` flag (behavior-neutral)
Delete `ScraperConfig.remove_scripts`. Script/style/noscript removal is
already fully driven by `blocked_tags`, so removing the flag changes no
behavior. Update `docs/content-scraper.md` to drop the field from the
`ScraperConfig` field list and remove the "dead flag" note. Update
`tests/test_scraper.py::test_default_config` (which asserts
`config.remove_scripts is True`) to drop that assertion.

### Hole 2 — make `word_count` consistent with the returned `raw_text`
Recompute `word_count` AFTER the `max_content_length` truncation, so
`word_count == len(result.raw_text.split())` always holds for the returned
object. State this in the `scrape` docstring (part 2, return-object fields):
"`word_count` is `len(raw_text.split())` of the (possibly truncated)
`raw_text`".

## Acceptance criteria
- `ScraperConfig` has no `remove_scripts` field; `HTMLScraper` behavior is
  unchanged for every existing `blocked_tags` configuration.
- For any `html` and `max_content_length`, `scrape` returns a
  `ScrapedContent` where `word_count == len(result.raw_text.split())`.
- `docs/content-scraper.md` reflects both changes (field list + the
  `word_count` computation ordering) and is shipped in the SAME PR.

## Pinning tests to add (in `tests/test_scraper.py`)
- **Hole 2 (normal + guard path):** one test that scrapes a page whose
  `raw_text` exceeds a small `max_content_length` (e.g. 100) and asserts
  `result.word_count == len(result.raw_text.split())` AND
  `len(result.raw_text) <= 100`; alongside a short-page case (no truncation)
  asserting the same equality. One returned object pins both the truncation
  path and the normal path.
- **Hole 1:** after the flag is removed, `test_default_config` no longer
  references `remove_scripts`; add a test that a page with a `<script>` tag
  still has its script text excluded from `raw_text` under the default
  `blocked_tags` (pins that removal is driven by `blocked_tags`, not the
  removed flag).

## Docs update (SAME PR)
`docs/content-scraper.md`:
- Remove `remove_scripts` from the `ScraperConfig` field list.
- In `scrape` step 10/11 and the `ScrapedContent.word_count` field note,
  state that `word_count` is computed from the (possibly truncated)
  `raw_text`.
- Remove contract hole 1 (dead flag) and contract hole 2 (word_count) from
  the "Contract holes" section (they are now fixed); renumber the remaining
  holes.
