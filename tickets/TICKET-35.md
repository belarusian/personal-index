# TICKET-35: Type error — `rate_limiter.py` passes `int | None` to `float()` and `RateLimitStatus`

## Title
`TokenBucket.__init__` and `TokenBucket.status()` have type errors from nullable `burst_size` and `limit`

## Evidence
In `personal_index/rate_limiter.py:35-39`:
