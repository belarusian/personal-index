Status: IMPLEMENTED #994@bf53550
Kind: ARCH
Author: architect (cycle 169)
Issue: #985

# ARCH-4: `SearchIndex.add_page` docstring over-promise ("Returns page id.")

## Component
`personal_index.index.SearchIndex.add_page` (index.py line 84).

## Symptom
The docstring reads "Add a page to the index. Returns page id." but the body
returns `len(self._pages)` — the new page **count**, not a page id. There is no
page-id concept in `SearchIndex`; the docstring over-promises a "page id" that
does not exist.

## Public contract (the code is the truth)
`add_page(page: IndexedPage | CrawledPage) -> int`:
- **Guard path:** none on the input (both `IndexedPage` and `CrawledPage` are
  accepted). A `CrawledPage` is converted to an `IndexedPage` (domain via
  `url_utils.extract_domain`, `content_length=len(content)`, `crawled_at`
  isoformat'd when it has one, `score` from `relevance_score`); an
  `IndexedPage` is used as-is.
- **Behavior:** stores the page under `page.url` in `_pages`; tokenizes
  `f"{title} {content}"` and adds `page.url` to each token's `_word_index`
  list (deduped); persists via `_save()`.
- **Return:** the new page count, `len(self._pages)` (an `int`). NOT a page id.
- **Side effects:** mutates `_pages` and `_word_index`; persists to `db_path`
  via `_save()`.

## Acceptance criteria
- The docstring states the EXACT return (the new page count, `len(self._pages)`)
  and the `CrawledPage` -> `IndexedPage` conversion, not "page id".
- ONE pinning test asserts the RETURNED VALUE: add a page to a fresh index and
  assert the return is `1`; add a second distinct page and assert the return is
  `2`; re-add the SAME url and assert the return is still `2` (the count does
  not grow on a url overwrite) — the guard/default path (overwrite) alongside
  the normal path.

## Pinning tests to add
`test_add_page_returns_count_pinned` (normal + overwrite input), asserting the
returned int.

## Docs page it updates
`docs/search-index.md` (the `add_page` entry + the contract-holes line).
