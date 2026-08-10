# TICKET-94: Missing type annotations for empty collection variables across multiple modules

## Title
Multiple modules have variables initialized as empty collections without type annotations, causing mypy errors

## Evidence
mypy flags `[var-annotated]` errors in several files:

1. `personal_index/analytics.py:120` — `hourly` needs type annotation
2. `personal_index/analytics.py:121` — `daily` needs type annotation
3. `personal_index/analytics.py:139` — `domain_counter` needs type annotation
4. `personal_index/content_export_csv.py:112` — `columns` needs type annotation
5. `personal_index/content_export_csv.py:215` — `columns` needs type annotation
6. `personal_index/queue.py:233` — `status_counts` needs type annotation
7. `personal_index/link_analyzer.py:126` — `all_domains` needs type annotation

These are all cases where a variable is initialized as `Counter()`, `set()`, or `dict()` without an explicit type annotation, and mypy cannot infer the generic parameters.

## Impact
Type checking fails for these variables. Downstream code using these variables may also fail type checking.

## Suggestion
Add explicit type annotations to each:
- `hourly: Counter[str] = Counter()`
- `daily: Counter[str] = Counter()`
- `domain_counter: Counter[str] = Counter()`
- `columns: set[str] = set()`
- `status_counts: dict[str, int] = {}`
- `all_domains: set[str] = set()`
