# TICKET-315: rate_limiter.RateLimiter.can_request docstring hides a token-consuming side effect

- Status: RESOLVED (merged to main fd70139, gh #467 closed, gh #466 closed)
- Module: personal_index/rate_limiter.py
- Defect class: (b) doc/behavior drift — docstring promises a pure "check" but the body consumes a token
- Issue: #466

## Symptom
`RateLimiter.can_request(domain)` (rate_limiter.py:105) is documented as
"Check if a request to the domain is allowed." — the wording of a pure,
side-effect-free predicate. But the body is `return bucket.acquire()`, and
`TokenBucket.acquire()` (rate_limiter.py:52) **decrements the token count**
when it succeeds. So every `can_request` call silently spends one token from
the domain's budget, even though the docstring frames it as a read-only
check. A caller who "checks" N times has actually consumed N tokens.

## Evidence (verified at runtime, cycle 67)
Default config burst_size=10:
- `get_status('x.com').remaining` -> 10
- `can_request('x.com')` -> True ; `get_status('x.com').remaining` -> 9
- `can_request('x.com')` -> True ; `get_status('x.com').remaining` -> 8
Two "checks" consumed two tokens. The consuming behavior is the intended,
tested design (tests/test_rate_limiter.py:92-156 repeatedly call can_request
and expect the budget to exhaust), so the body is correct and the docstring
is the defect.

## Fix (minimal, additive)
Make the docstring honestly document the side effect, e.g.:
    """Check if a request to the domain is allowed.

    Consumes one token from the domain's budget when the request is
    allowed (returns True); returns False without consuming a token when
    the budget is exhausted.
    """
Add a regression test asserting that a successful `can_request` decrements
the reported remaining token count by one (pinning the documented side
effect), and that a failed `can_request` does not.
