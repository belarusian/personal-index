# TICKET-DTZ001: `datetime.datetime()` called without `tzinfo` argument

## Category
DTZ001 — datetime() called without tzinfo

## Evidence
24 occurrences across 10 test files:

| File | Line |
|------|------|
| tests/test_content_batch.py | 26, 27 |
| tests/test_content_export_csv.py | 150 |
| tests/test_content_notifications.py | 70 |
| tests/test_content_search.py | 132, 133, 136, 141, 142, 145 |
| tests/test_content_validation.py | 117 |
| tests/test_scheduler.py | 143, 144, 150, 151, 204, 209 |
| tests/test_serializer.py | 49, 122 |
| tests/test_sitemap_builder_syntax_fix.py | 28 |
| tests/test_stats.py | 161, 167, 170, 171 |

## Impact
Naive datetimes in tests can mask timezone-related bugs in production code. If the tested modules expect timezone-aware datetimes, these tests may pass locally but fail in CI or production with different system timezones.

## Suggestion
Pass `tzinfo=datetime.timezone.utc` (or `datetime.now(datetime.timezone.utc)` for `now()`) to every `datetime()` call in these test files. For test fixtures, consider using a helper like `datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)`.
