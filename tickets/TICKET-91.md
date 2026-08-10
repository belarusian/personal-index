# TICKET-91: Type error — `analytics.py` iterates `_crawl_events` but variable typed as `SearchEvent`

## Title
Loop variable `e` in `AnalyticsTracker.get_summary()` inferred as `SearchEvent` but used as `CrawlEvent`

## Evidence
File: `personal_index/analytics.py`
Lines 139-141:
