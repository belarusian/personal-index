# TICKET-328 — content_summarizer module docstring drift (TF-IDF over-promise)

- Status: OPEN
- Class: (b) doc/behavior drift
- File: personal_index/content_summarizer.py
- Issue: #494

## Symptom
The module docstring (line 4) promises sentence scoring "based on keyword
frequency and TF-IDF-like metrics", but the module implements no TF-IDF /
inverse-document-frequency component at all. Scoring is pure keyword frequency:
`_word_frequency()` counts word occurrences, `_score_sentence()` returns
`sum(word_freq[w] for w in words) / len(words)` (plus first/last-sentence
boosts in `_score_and_select`). No `idf`, `log`, or document-frequency term
exists anywhere in the module.

## Evidence
- `grep -n 'tf\|idf\|TF\|IDF\|log\|document_freq\|doc_freq' personal_index/content_summarizer.py`
  → only line 4 (the docstring) matches; no IDF/log/doc-freq code.
- `_score_sentence` (lines 79-86): score = sum of raw word frequencies / len(words).

## Minimal additive fix
Correct the module docstring to describe the actual signal: "sentence scoring
based on keyword frequency" (drop the TF-IDF-like claim). Add ONE regression
test `TestModuleDocstringContract::test_docstring_does_not_promise_tfidf` that
asserts "tf-idf" / "idf" is absent from `module.__doc__`.

## Triage
Verified genuine against code. Not a documented design constraint, not
seed-internal. Same drift pattern as TICKET-327 (content_recommender).
