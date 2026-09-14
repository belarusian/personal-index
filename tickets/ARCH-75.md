# ARCH-75 — tfidf: `add_document` counts a zero-term (empty/all-stopword) document toward the corpus, inflating the IDF denominator and shifting every existing document's TF-IDF score

Status: CLAIMED 2026-09-14
Component: `personal_index/tfidf.py` — `TfidfScorer.add_document` (lines 20-30); the IDF expression in `TfidfScorer.compute_tfidf` (line 59); the `add_document` docstring (line 21)
Umbrella: ARCH-2 (#983)
Issue: #1413
Docs: `docs/tfidf.md` (Contract Hole 1)

## Problem
`add_document` increments `self._doc_count` **unconditionally**, but only tokens
that survive `tokenize(text, remove_stopwords=True)` enter `self._doc_freq`. A
document whose text tokenizes to zero terms (empty string, whitespace, or
all-stopwords) therefore raises `_doc_count` while contributing nothing to any
term's document-frequency.

`compute_tfidf`'s IDF is `log((1 + _doc_count) / (1 + df)) + 1`, so that extra
`_doc_count` inflates the IDF — and hence the TF-IDF score — of **every
existing term in the corpus**. The empty document itself is invisible in the
output (`compute_tfidf` -> `{}`, `score_query` -> `0.0`, never ranked), so the
score shift is silent: no exception, no warning, and the empty doc never
appears in any result.

Verified (cycle 243):

    s = TfidfScorer()
    d0 = s.add_document('cat sat')
    s.compute_tfidf(d0)          # {'cat': 0.5, 'sat': 0.5}
    s.add_document('')           # _doc_count 1 -> 2, _doc_freq unchanged
    s.compute_tfidf(d0)          # {'cat': 0.7027325540540822, 'sat': 0.7027325540540822}
    s.rank_documents('cat')      # [(0, 0.7027325540540822)]  (was 0.5)
    s.remove_document(<empty id>) # restores {'cat': 0.5, 'sat': 0.5}

The `add_document` docstring ("Add a document to the corpus. Returns document
ID.") never states that a zero-term document still counts toward the corpus
size and thereby inflates every other document's IDF. This is the same
"public path silently does the thing the docstring omits" class as ARCH-72 /
ARCH-74.

## Public contract (recommended)
`add_document(self, text: str) -> int`:
- A document whose text tokenizes to **zero terms** (empty / whitespace /
  all-stopwords) must **not** increment `_doc_count` and must **not** be stored
  in `_doc_terms` — it is a no-op that returns the next id without disturbing
  the corpus. (Equivalently: `_doc_count` counts only documents that
  contribute at least one term to `_doc_freq`, so the IDF denominator reflects
  the number of documents that actually contain terms.)
- A document with one or more surviving terms behaves **exactly as today**
  (id assigned, `_doc_count` incremented, `_doc_freq` bumped per unique token).
- `remove_document`, `compute_tfidf`, `score_query`, `rank_documents`,
  `get_top_terms`, `document_count`, `vocabulary_size`, `clear` are unchanged.

The `add_document` docstring must state this exact conditional (a zero-term
document is a no-op that does not count toward the corpus) rather than the
current blanket "Add a document to the corpus. Returns document ID."

## Acceptance criteria
1. `s.add_document('cat sat')` then `s.add_document('')` leaves
   `s.compute_tfidf(<first id>) == {'cat': 0.5, 'sat': 0.5}` — the empty doc
   does not shift the existing scores (the hole is closed).
2. `s.document_count` after `add_document('cat sat')` + `add_document('')` is
   `1` (the zero-term doc is not counted).
3. `s.add_document('the')` (all-stopwords) is also a no-op: `document_count`
   unchanged, `vocabulary_size` unchanged, existing scores unchanged.
4. A normal document still works: `s.add_document('cat sat')` +
   `s.add_document('dog runs')` gives `document_count == 2` and the IDF
   reflects two documents (behavior identical to today for non-empty docs).
5. `remove_document` of a previously-added zero-term id returns `False` (it was
   never stored) and leaves the corpus untouched.

## Pinning tests to add (tests/test_tfidf.py)
- **IDF-inflation pin (the hole):** build a scorer, `d0 = add_document('cat
  sat')`, assert `compute_tfidf(d0) == {'cat': 0.5, 'sat': 0.5}`; then
  `add_document('')` and assert `compute_tfidf(d0)` is STILL
  `{'cat': 0.5, 'sat': 0.5}` (not `0.7027...`) — pins the corrected behavior
  against the returned object, not the docstring.
- **Guard-path pin (all-stopwords):** `add_document('the')` after a real doc
  leaves `document_count` and `vocabulary_size` unchanged and existing scores
  unchanged — pins the zero-term guard for the all-stopwords input, not just
  the empty string.
- **Normal-doc pin:** two real documents give `document_count == 2` and the
  two-doc IDF (e.g. `compute_tfidf` of a term present in only one of the two
  docs uses the 2-doc denominator) — pins that non-empty docs are unchanged.
- **No-op-remove pin:** the id returned by a zero-term `add_document` is not in
  the corpus: `remove_document(<that id>)` returns `False` and the corpus is
  untouched.

## Docs (SAME PR)
`docs/tfidf.md` (new, spec) + the `tfidf.md` index entry in docs/README.md ship
in the same PR as this ticket.
