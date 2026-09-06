# TICKET-506: AnalyticsTracker._extract_domain docstring under-specifies contract

- **File:** personal_index/analytics.py
- **Method:** `AnalyticsTracker._extract_domain` (line 371)
- **Defect class:** (b) docstring drift (under-specification)
- **Symptom:** Docstring is a blanket one-liner "Extract domain from URL." that omits the exact behavior the body performs.
- **Evidence (line 371-379):**
     def _extract_domain(url: str) -> str | None:
        """Extract domain from URL."""
        if not url:
            return None
        try:
            return url.split("://")[1].split("/")[0] if "://" in url else url.split("/")[0]
        except (IndexError, AttributeError):
            return None
     Actual behavior:
    1. Falsy url (empty string / None) -> returns None.
   2. Scheme-prefixed url (contains "://") -> returns the segment between "://" and the first "/" (host, including any port; port is NOT stripped).
   3. Scheme-less url -> returns the segment before the first "/".
   4. If the split raises IndexError/AttributeError -> returns None.
   Note: unlike url_utils.extract_domain, this does NOT strip a port and does NOT lowercase.
- **Minimal additive fix:** Reword the docstring to enumerate the exact conditional branches above; add ONE behavior test pinning the corrected claim against the returned value, including the guard-path input (falsy url -> None) and the currently-untested scheme-less branch alongside the normal case.
- **Issue:** #866
- **Status:** RESOLVED (merged via PR #867, CI run 34034871507, gh #866 closed)
