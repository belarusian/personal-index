# TICKET-24: Duplicate `CrawlConfig` dataclasses in `models.py` and `config/__init__.py`

## Title
Two `CrawlConfig` dataclasses with different field schemas

## Evidence
Two distinct `CrawlConfig` classes:

1. **`personal_index/models.py:111`** — Has `max_depth`, `politeness_delay`, `rate_limit`, `max_pages_per_domain`, `timeout`, `user_agent`, `respect_robots_txt`, `allowed_domains`, `blocked_domains`
2. **`personal_index/config/__init__.py:35`** — Has `max_depth`, `politeness_delay`, `delay`, `rate_limit`, `max_pages`, `max_pages_per_domain`, `allowed_domains`, `blocked_extensions`, `user_agent`, `respect_robots_txt`, `timeout`, `max_concurrent_requests`, `request_timeout`

Import usage:
- `models.py` CrawlConfig: imported by `storage.py:5`
- `config/__init__.py` CrawlConfig: not directly imported by other modules (dead code)

## Impact
- `config/__init__.py`'s `CrawlConfig` has extra fields (`delay`, `max_concurrent_requests`, `request_timeout`, `blocked_extensions`) that `models.py` lacks
- `storage.py` uses `models.py`'s version, so config fields are silently lost
- `config/__init__.py`'s version appears to be dead code

## Suggestion
1. Merge fields into a single `CrawlConfig` in `models.py`
2. Remove `CrawlConfig` from `config/__init__.py`
3. Also consider removing `Interest` from `config/__init__.py` (see TICKET-21)
