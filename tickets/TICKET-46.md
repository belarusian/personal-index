# TICKET-46: Deprecated datetime.utcnow() — content_enricher.py:31

## Title
datetime.utcnow() is deprecated and scheduled for removal in Python 3.12+

## Evidence
In personal_index/content_enricher.py:31:

    enriched_at: datetime = field(default_factory=datetime.utcnow)

Python datetime.utcnow() is deprecated since Python 3.12 and will be removed in a future version. The deprecation warning is triggered during test runs:

    tests/test_content_enricher.py: 21 warnings
      <string>:14: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).

## Impact
- Deprecation warnings flood test output (21 warnings per test run)
- Code will break when Python removes datetime.utcnow() in a future release
- Naive datetime objects are ambiguous (no timezone info)

## Suggestion
Replace datetime.utcnow with datetime.now(datetime.timezone.utc) to use timezone-aware datetime objects:

    enriched_at: datetime = field(default_factory=lambda: datetime.now(datetime.timezone.utc))
