# TICKET-20: Four duplicate `SearchIndex` classes across the codebase

## Title
Four different `SearchIndex` classes exist in separate modules, causing confusion and fragmentation

## Evidence
Four distinct `SearchIndex` classes are defined:

1. **`personal_index/index.py:80`** — `SearchIndex` with `db_path: str | None`, stores `IndexedPage` from `index.py`
2. **`personal_index/search_index.py:16`** — `SearchIndex` with `index_path: str`, stores `CrawledPage` from `models.py`
3. **`personal_index/indexer.py:13`** — `SearchIndex` with `index_dir: str | Path | None`, stores `Page` from `models.py`, uses TF-IDF scoring
4. **`personal_index/content_search_fulltext.py:179`** — `SearchIndex` with BM25 ranking, stores `dict[str, dict]`

Import usage:
- `cli.py:9` imports from `personal_index.index`
- `results.py:11`, `stats.py:10`, `scheduler.py:13` import from `personal_index.search_index`
- `personal_index/indexer.py` — **never imported by any other module** (dead code)
- `personal_index/content_search_fulltext.py` — **never imported by any other module** (dead code)

## Impact
- Developers don't know which `SearchIndex` to use
- Two implementations (`indexer.py`, `content_search_fulltext.py`) are dead code, wasting maintenance effort
- Each class has a different API, data model, and persistence strategy
- Bug fixes must be applied to multiple classes independently

## Suggestion
1. Audit which `SearchIndex` is actually used in production paths
2. Consolidate into a single `SearchIndex` class in `personal_index/search_index.py`
3. Remove dead implementations (`indexer.py`, `content_search_fulltext.py`) or mark them as deprecated
4. Unify the data model (use `models.py` types consistently)
