# tfidf — TF-IDF scoring for document relevance ranking

Module: `personal_index/tfidf.py` (122 lines). Live production module:
dedicated `tests/test_tfidf.py` + `tests/deep/test_tfidf_adversarial.py`.
Distinct from `personal_index/search_index.py` (the `SearchIndex` page) —
this is a standalone in-memory TF-IDF scorer with no persistence.

## Public API

`class TfidfScorer` (line 11) — in-memory TF-IDF scorer. No constructor args;
state is four private fields (`_doc_freq`, `_doc_count`, `_doc_terms`,
`_next_id`).

- `__init__(self)` (line 14) — empty corpus; `_next_id` starts at 0.
- `add_document(self, text: str) -> int` (line 20) — tokenizes `text` with
  `tokenize(text, remove_stopwords=True)`, stores the term `Counter` under a
  fresh id, increments `_doc_count`, and bumps each unique token's
  document-frequency. Returns the new id (0, 1, 2, ...). **A text that
  tokenizes to zero terms (empty / whitespace / all-stopwords) still
  increments `_doc_count` and returns a valid id, but contributes nothing to
  `_doc_freq`** — see Contract Hole 1.
- `remove_document(self, doc_id: int) -> bool` (line 32) — removes the doc,
  decrements `_doc_count`, and decrements each of its tokens' document-frequency
  (deleting the key when it reaches 0). Returns `False` for an unknown
  `doc_id` (idempotent: a second remove of the same id returns `False`).
- `compute_tfidf(self, doc_id: int) -> dict[str, float]` (line 45) — returns
  `{}` for an unknown `doc_id`, an empty corpus (`_doc_count == 0`), or a doc
  whose terms sum to 0. Otherwise per term: `tf = count / total_terms`,
  `idf = log((1 + _doc_count) / (1 + df)) + 1`, score `= tf * idf`.
- `score_query(self, query: str, doc_id: int) -> float` (line 62) — dot product
  of the query's normalized-term-frequency vector and the doc's TF-IDF vector.
  Returns `0.0` when the query tokenizes to no terms (all-stopwords) or the
  `doc_id` is not in the corpus.
- `rank_documents(self, query: str, limit: int = 10) -> list[tuple[int, float]]`
  (line 82) — all docs with `score_query > 0`, sorted by score descending,
  truncated to `limit`. **Returns `[]` when `limit <= 0`.**
- `document_count` (property, line 98) — `_doc_count`.
- `vocabulary_size` (property, line 103) — `len(_doc_freq)`.
- `get_top_terms(self, doc_id: int, n: int = 10) -> list[tuple[str, float]]`
  (line 107) — the doc's TF-IDF terms sorted by score descending, truncated to
  `n`. **Returns `[]` when `n <= 0`.**
- `clear(self) -> None` (line 117) — resets all four fields (corpus empty,
  `_next_id` back to 0).

## Contract Hole 1 — an empty document inflates the IDF denominator for every existing term (ARCH-75)

`add_document` increments `_doc_count` **unconditionally**, but only tokens
that survive `tokenize(..., remove_stopwords=True)` enter `_doc_freq`. So a
document whose text tokenizes to zero terms (empty string, whitespace, or
all-stopwords) raises `_doc_count` while contributing nothing to any term's
document-frequency. Because `compute_tfidf`'s IDF is
`log((1 + _doc_count) / (1 + df)) + 1`, that extra `_doc_count` inflates the
IDF — and therefore the TF-IDF score — of **every existing term in the corpus**.

Verified (cycle 243):

    s = TfidfScorer()
    d0 = s.add_document('cat sat')
    s.compute_tfidf(d0)          # {'cat': 0.5, 'sat': 0.5}
    s.add_document('')           # empty doc: _doc_count 1 -> 2, _doc_freq unchanged
    s.compute_tfidf(d0)          # {'cat': 0.7027325540540822, 'sat': 0.7027325540540822}
    s.rank_documents('cat')      # [(0, 0.7027325540540822)]  (was 0.5)

The empty document's own `compute_tfidf` is `{}` (its terms sum to 0) and it
never appears in `rank_documents` (score 0.0) — so the corruption is silent:
the empty doc is invisible in the output, yet it has shifted the scores of
every other document. `remove_document` of the empty doc restores the original
scores (verified: back to `{'cat': 0.5, 'sat': 0.5}`), confirming the shift is
entirely attributable to the empty doc's `_doc_count` contribution.

The `add_document` docstring ("Add a document to the corpus. Returns document
ID.") never states that a zero-term document still counts toward the corpus
size and thereby inflates every other document's IDF. This is the same
"public path silently does the thing the docstring omits" class as ARCH-72 /
ARCH-74.

## Secondary notes (verified, NOT holes)
- `remove_document` is idempotent and returns `False` for an unknown id; it
  fully cleans up `_doc_freq` (deletes keys at 0), so `vocabulary_size` is
  accurate after removals.
- `compute_tfidf` / `score_query` / `get_top_terms` all guard the empty/unknown
  cases with `{}` / `0.0` / `[]` — no division-by-zero on an empty corpus or a
  zero-term doc.
- `rank_documents(limit <= 0)` and `get_top_terms(n <= 0)` both return `[]`
  (documented in their docstrings).
