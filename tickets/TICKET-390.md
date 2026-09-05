# TICKET-390: rate_limit_middleware.py RateLimitMiddleware.__call__ placeholder docstring (class-(b) doc-drift)

Status: RESOLVED

## File
personal_index/api/rate_limit_middleware.py

## Symptom
`RateLimitMiddleware.__call__` (line 198) carries a generic
`"""Process request with rate limiting."""` placeholder that does not describe
the exact behavior the body performs.

## Evidence
- L198-199: `async def __call__(self, scope, receive, send):` with
  `"""Process request with rate limiting."""`
- Body behavior (L200-244):
  1. If `scope["type"] != "http"`, it delegates straight to `self.app` and
     returns (no rate limiting applied to non-HTTP scopes).
  2. Otherwise it derives the client identifier via `self.key_extractor(scope)`
     (default: the client IP from `scope["client"][0]`, or `"unknown"`), and the
     method/path from the scope (defaulting to `"GET"` / `"/"`).
  3. It calls `self.limiter.is_allowed(identifier, method, path)` which returns
     `(allowed, headers)`.
  4. If NOT allowed, it short-circuits: it sends an `http.response.start` with
     status 429 and the rate-limit headers (e.g. `Retry-After`,
     `X-RateLimit-Limit`, `X-RateLimit-Remaining`), then an
     `http.response.body` of `b'{"error": "Rate limit exceeded"}'`, and does NOT
     call the wrapped app.
  5. If allowed, it wraps `send` in `add_headers`, which appends the rate-limit
     headers to the `http.response.start` message, and calls
     `self.app(scope, receive, add_headers)` so the app's response carries the
     `X-RateLimit-*` headers.

## Minimal additive fix
Reword the placeholder to state the exact behavior: for non-HTTP scopes it
delegates to the wrapped app unchanged; for HTTP scopes it resolves the client
identifier (via the key extractor), method, and path, asks the limiter whether
the request is allowed, and either (a) short-circuits with a 429 response
carrying the rate-limit headers and a JSON error body without invoking the app,
or (b) invokes the app with a wrapped `send` that appends the `X-RateLimit-*`
headers to the response start. Add ONE pinning behavior test that witnesses the
ALLOWED path: a request within the limit passes through to the app AND the
`http.response.start` message the app emits is augmented with the
`X-RateLimit-Limit` / `X-RateLimit-Remaining` headers (witnessing the
header-injection claim, not just that the app ran).

Issue: #618

## Status
RESOLVED - merged to main 71a8a75 via PR #619 (squash); gh #618 closed; CI run 33942532581 green (test 3.10/3.11/3.12 all pass).
