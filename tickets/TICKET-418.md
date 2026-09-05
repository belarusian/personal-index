# TICKET-418

- Status: OPEN
- Class: (b) doc-drift (blanket docstring, no sub-component enumeration)
- File: personal_index/content_summarizer.py
- Function: summarize (lines 155-171)

## Symptom
The `summarize` docstring is a blanket over-promise:
"Generate an extractive summary of the given text."
It does NOT enumerate the actual sub-components the body performs:
  1. Guard path: `if not text or len(text) < min_length` (default 50) ->
     `_no_op_result(text)` (SummaryResult with summary=text, ratio=1.0,
     sentences=[text] if text else [], word counts from `_tokenize`).
  2. Short-text path: if sentence count (via `_split_sentences`) is
     `<= max_sentences` (default 3) -> `_build_summary_result(text, sentences)`
     keeping ALL sentences (no scoring).
  3. Scoring path: otherwise computes `_word_frequency(text)` and selects
     top `max_sentences` via `_score_and_select` (first sentence boosted ×2.5,
     last ×1.1), then `_build_summary_result(text, selected)`.
  4. Returns SummaryResult(original_text, summary, sentences, ratio,
     word_count_original, word_count_summary).

## Evidence
- personal_index/content_summarizer.py:159 (docstring)
- personal_index/content_summarizer.py:160-161 (guard `return _no_op_result`)
- personal_index/content_summarizer.py:163-164 (short-text path)
- personal_index/content_summarizer.py:166-168 (scoring path)

## Minimal additive fix
Reword the docstring to state the EXACT behavior: enumerate the guard path
(falsy/short text -> _no_op_result), the short-text path (all sentences kept),
the scoring path (word_freq + score_and_select with boosts), and the
SummaryResult fields. Add ONE pinning test asserting the RETURNED SummaryResult
object fields (summary, sentences, ratio, word_count_original, word_count_summary)
for the normal scoring case AND the guard-path input (empty text -> summary="",
sentences=[], ratio=1.0) so one test pins both the main behavior and the guard path.

## Issue: #674
