# TICKET-28: Type error — `store_path` is `str | None` but passed to `open()` without null check

## Title
Multiple modules pass `str | None` path to `open()` without checking for `None`

## Evidence
mypy reports `arg-type` errors in multiple modules where a `str | None` field is passed directly to `open()`:

1. **`personal_index/interests.py:63`** — `InterestStore.store_path: str | None = None`, passed to `open(self.store_path, "r")`
2. **`personal_index/index.py:94`** — `SearchIndex.db_path: str | None = None`, passed to `open(self.db_path, "r")`
3. **`personal_index/domains.py:63`** — `DomainManager.rules_file: str | None = None`, passed to `open(self.rules_file, "r")`
4. **`personal_index/tags.py:47`** — `TagStore.store_path: str | None = None`, passed to `open(self.store_path, "r")`

All four follow the same pattern: `__post_init__` guards with `if self.path and os.path.exists(self.path)`, but `_load()` is called unconditionally and passes the potentially-`None` path to `open()`.

## Impact
- `TypeError` at runtime if `_load()` is called when path is `None`
- The `__post_init__` guard prevents this in normal usage, but `_load()` could be called manually after initialization

## Suggestion
Add a guard in `_load()`:
