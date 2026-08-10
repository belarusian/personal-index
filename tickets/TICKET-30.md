# TICKET-30: Type error — `SearchIndex` in `indexer.py` passes `Page` to `SearchResult` expecting `IndexedPage`

## Title
`indexer.py` constructs `SearchResult(page=page)` where `page` is `Page` but `SearchResult.page` expects `IndexedPage`

## Evidence
In `personal_index/indexer.py:122-123`:
