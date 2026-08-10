# TICKET-11: Broken test imports — tests reference non-existent or broken modules

## Title
4 test files have broken imports due to missing modules or syntax errors in source

## Evidence
Running import checks on all test files reveals 4 broken imports:

| Test File | Error | Source |
|-----------|-------|--------|
| `tests/test_content_pin.py:2` | `ModuleNotFoundError: personal_index.content_pin` | Module does not exist |
| `tests/test_content_priority.py` | `SyntaxError: unmatched ')'` | `content_priority.py:374` (TICKET-7) |
| `tests/test_content_versioning.py:2` | `ModuleNotFoundError: personal_index.content_versioning` | Module does not exist |
| `tests/test_sitemap_builder.py` | `SyntaxError: invalid syntax` | `sitemap_builder.py:53` (TICKET-8) |

Additionally, from TICKET-1, these test files also reference non-existent modules:
- `tests/test_content_changelog.py` → `personal_index.content_changelog`
- `tests/test_content_diff.py` → `personal_index.content_diff`
- `tests/test_content_rollback.py` → `personal_index.content_rollback`

## Impact
- These tests will fail on import, polluting test output
- CI/CD may report false failures
- Developers may waste time debugging import errors

## Suggestion
1. Fix `content_priority.py` and `sitemap_builder.py` (TICKET-7, TICKET-8)
2. For non-existent modules (`content_pin`, `content_versioning`, `content_changelog`, `content_diff`, `content_rollback`):
   - Either implement the missing modules
   - Or remove the orphaned test files
3. Add a pre-commit hook to verify all test imports resolve
