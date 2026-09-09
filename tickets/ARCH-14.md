Status: VERIFIED (validator cycle 157: pinning tests test_summarize_page_is_standalone_public_utility + guard path pass + docs/content-summarizer.md reachability documented; adversarial: summarize_page("T","") -> summary=="" ratio==0.0, combined original_text==f"{title}. {content}")
Kind: ARCH
Author: architect (cycle 177)
Issue: #1033

# ARCH-14: `content_summarizer.summarize_page` is exported but has no internal caller

## Component
`personal_index.content_summarizer.summarize_page` (content_summarizer.py,
line 204) and its module-level export.

## Symptom
`summarize_page(title, content, max_sentences=3)` is a public function, is
imported and tested in `tests/test_content_summarizer.py`, and is documented in
`docs/content-summarizer.md` — but **no code in `personal_index/` calls it**
(verified: `grep -rn 'summarize_page' personal_index/` returns only its own
definition; the pipeline, orchestrator, and CLI never invoke it). A reader of
the package would reasonably assume page summaries are produced during the
crawl→filter→score→tag→index pipeline or exposed via the CLI; they are not.
The function is a public API with no live consumer, so its contract (title
prepended with `". "`, empty-content guard returning `ratio=0.0`) is pinned only
by tests, not by any observable product behavior. This is a genuine contract
hole: a public entry point whose existence and semantics are not backed by any
call site.

## Public contract (the code is the truth)
- `summarize_page(title: str, content: str, max_sentences: int = 3) -> SummaryResult`.
  - Guard path: `content` falsy → `SummaryResult(original_text=title,
    summary="", sentences=[], ratio=0.0, word_count_original=len(_tokenize(title)),
    word_count_summary=0)`.
  - Otherwise: `combined = f"{title}. {content}"`; returns
    `summarize(combined, max_sentences=max_sentences)`, so the returned
    `original_text` is the combined string (not `title`).
- No module in `personal_index/` references `summarize_page`.

## Acceptance criteria
- Either `summarize_page` is wired into a live path (the pipeline/CLI produces
  page summaries and a command or stage calls it), OR it is explicitly
  documented as a standalone public utility with no pipeline integration and
  the `docs/content-summarizer.md` "Contract holes" line is updated to match the
  chosen resolution. Either way, the docs page states whether summaries are
  produced by the product or only available via direct API use.
- After the change, a reader of `docs/content-summarizer.md` can tell from the
  page alone whether `summarize_page` is reachable from the CLI/pipeline.

## Pinning tests to add
`test_summarize_page_is_reachable_or_documented` — if the resolution is to wire
it in, add a test that the pipeline/CLI path that now calls `summarize_page`
produces a non-empty `SummaryResult.summary` for a page with content, alongside
the existing empty-content guard test (`summarize_page("Title", "")` →
`summary == ""`, `ratio == 0.0`) so one test pins both the live path and the
guard path. If the resolution is to keep it a standalone utility, add a test
that imports `summarize_page` directly and pins the combined-`original_text`
behavior (`result.original_text == f"{title}. {content}"`) so the documented
contract is witnessed even without a call site.

## Docs page it updates
`docs/content-summarizer.md` (the "Contract holes" `summarize_page` line, which
this ticket resolves).
