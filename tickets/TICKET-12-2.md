# TICKET-12-2: Refactor `stats.StatsCollector.get_index_stats` (58L, line 45)

## What's wrong

`StatsCollector.get_index_stats` in `personal_index/stats.py` (line 45) is 58 lines and performs a single pass over all pages while accumulating 7 different statistics simultaneously:
1. Total word count
2. Total content length
3. Domain frequency counts
4. Interest frequency counts
5. Pages-with-interests counter
6. Timestamp collection
7. Page count

The accumulation loop mixes concerns: domain extraction, content analysis, interest tracking, and timestamp collection are all interleaved in one `for` body.

## Evidence
