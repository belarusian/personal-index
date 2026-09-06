# TICKET-480: ContentNormalizer._normalize_url generic docstring (class-(b) doc-drift)

- File: personal_index/content_transform/normalizer.py
- Method: ContentNormalizer._normalize_url
- Symptom (class-(b) doc-drift): the docstring is the generic "Normalize URL
  format." but the code does three specific, contract-bearing things:
  1. strips surrounding whitespace;
  2. prepends "https://" when the stripped value is non-empty and does not
     already start with "http";
  3. removes trailing "/" characters from the result when it is longer than
     one character.
- Evidence line: `url = url.strip()` / `if url and not url.startswith("http"):`
  / `if len(url) > 1: url = url.rstrip("/")`.
- NOTE (verified against code, briefing correction): the briefing claimed a
  "lone-slash exception" where "/" stays "/". This is FALSE. Because the
  "https://" prefix is added BEFORE the trailing-slash strip, "/" becomes
  "https:///" then rstrip("/") -> "https:". The `len(url) > 1` guard never
  preserves a lone slash (a lone "/" is never 1-char at that point). The
  docstring and pinning tests therefore pin the ACTUAL behavior, not the
  briefing's incorrect claim.
- Minimal additive fix: reword the docstring to state the three actual
  behaviors; add a pinning test class TestNormalizeUrlPinning in
  tests/test_content_transform.py covering the verified behaviors.
- Status: OPEN
- Issue: #812
