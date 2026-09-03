# TICKET-317: url_utils.extract_domain corrupts IPv6 literals without an explicit port

- Status: RESOLVED (merged to main 21b8132, gh #471 merged, gh #468 closed)
- Issue: #468
- Module: personal_index/url_utils.py
- Defect class: (a) logic bug — port-stripping `rsplit(":", 1)` also strips the last colon
  of a bracketed IPv6 literal when no port is present.
- NOTE: originally ticketed as TICKET-316; renumbered to TICKET-317 because a concurrent
  PR #470 (content_linker) landed TICKET-316 first and clobbered the namespace (cycle-45
  Lesson #1 collision). This is a DIFFERENT module (url_utils) — no code collision.

## Symptom
`extract_domain(url)` (url_utils.py:106) strips a port with:
    if ":" in netloc:
        netloc = netloc.rsplit(":", 1)[0]
For a bracketed IPv6 host with NO explicit port, the netloc still contains internal
colons (e.g. `[::1]`), so `rsplit(":", 1)` chops the last colon off the literal and
returns a corrupted, non-matching domain.

## Evidence (verified at runtime, cycle 46)
- `extract_domain("http://[::1]/path")`        -> `'[:'`        (should be `'[::1]'`)
- `extract_domain("http://[2001:db8::1]/")`    -> `'[2001:db8:'` (should be `'[2001:db8::1]'`)
- `extract_domain("http://[::1]:8080/p")`      -> `'[::1]'`      (correct — explicit port)
- `extract_domain("http://example.com:8080/")` -> `'example.com'` (correct — unchanged)
No test in tests/test_url_utils.py covered IPv6 literals before this fix.

## Impact
`extract_domain` is the domain authority used by `content_filter._is_blocked_domain`
(content_filter.py:96) and domain grouping. A blocked-domain entry for an IPv6 host
would never match because the extracted key is corrupted (`'[:'`), silently defeating
the block. Hostname and IPv6-with-port paths are unaffected.

## Fix (minimal, additive)
When the netloc is a bracketed IPv6 literal, keep the bracketed host intact (drop only
a trailing `:port` after the closing bracket); otherwise strip the port as before:
    netloc = parsed.netloc.lower()
    if netloc.startswith("["):
        bracket_end = netloc.find("]")
        if bracket_end != -1:
            netloc = netloc[: bracket_end + 1]
    elif ":" in netloc:
        netloc = netloc.rsplit(":", 1)[0]
    return netloc
Adds 5 regression tests (IPv6 with/without port, full literal, case normalization).
