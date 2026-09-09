# ARCH-61 — url_utils: `get_tld` returns only the LAST dot-label, so two-label TLDs and dotless hosts are silently wrong

Status: OPEN
Component: `personal_index/url_utils.py` — `get_tld` (lines 178-185)
Umbrella: ARCH-2 (#983)
Issue: #1201
Related: ARCH-60 (text_utils `read_time_minutes` unguarded division) — same "docstring over-promise / unenforced precondition" class
Docs: `docs/url-utils.md` (Domain / host extraction → `get_tld`)

## Problem
`get_tld` does `domain.split(".")` and returns `parts[-1]`:

    def get_tld(url: str) -> str:
        """Extract top-level domain from URL."""
        domain = extract_domain(url)
        if not domain:
            return ""
        parts = domain.split(".")
        return parts[-1] if parts else ""

This assumes a **single-label TLD**. The docstring says "Extract top-level
domain from URL" but never states the single-label-only precondition, so
callers cannot tell that two-label TLDs and dotless hosts produce
silently-wrong answers. Verified empirically on origin/main:

- `get_tld('https://example.com')` → `'com'` (correct, single-label).
- `get_tld('https://www.example.co.uk/x')` → `'uk'` (WRONG — the real TLD is
  `co.uk`; the second-level label is returned instead).
- `get_tld('https://example.com.au')` → `'au'` (WRONG — real TLD `com.au`).
- `get_tld('https://intranet')` → `'intranet'` (WRONG — a bare hostname has
  **no TLD**, yet the whole host is returned as if it were one).
- `get_tld('https://localhost:8080/x')` → `'localhost'` (same bare-host bug).
- `get_tld('')` → `''` (no netloc → no TLD, correct).
- `get_tld('not-a-url')` → `''` (no netloc → no TLD, correct).

The dotless-host case is the sharper bug: a host with no dot is not a TLD at
all, but the function returns the entire host. The two-label-TLD case is a
documented limitation (a full TLD requires a public-suffix lookup, which this
module deliberately does not do).

## Public contract (target)
State the precondition/limitation explicitly in the docstring: **`get_tld`
returns only the LAST dot-label of the domain, which is correct ONLY for
single-label TLDs (`com`, `org`, `net`).** It is NOT a full TLD resolver:

- For **two-label TLDs** (`co.uk`, `com.au`, `gov.uk`, …) it returns the
  second-level label (`uk`, `au`, `uk`), not the full TLD. Callers that need
  the full TLD must use a public-suffix lookup (e.g. the `tldextract`
  library); this module does not ship a suffix table.
- For **dotless hosts** (`localhost`, `intranet`, `192.168.0.1` is dotted so
  excluded) there is **no TLD**, and the function returns `""` — it must NOT
  return the whole host as if it were a TLD.

Pick ONE of the two options below and state it in the docstring so the
behavior is unambiguous:

Preferred option (document it in the docstring):
1. **Document the single-label-only limitation + return `""` for dotless
   hosts.** The two-label-TLD case remains returning the last label (documented
   as a known limitation, with a pointer to a public-suffix library for
   callers who need the full TLD). The dotless-host case changes from
   returning the whole host to returning `""` (no TLD). This is the minimal,
   additive, contract-clear fix: one behavioral change (dotless → `""`) plus
   a docstring that states the single-label-only precondition and the
   two-label limitation.
2. **Implement proper multi-label TLD handling** — a small known-two-label-TLD
   set (e.g. `co.uk`, `com.au`, `gov.uk`, `org.uk`, `com.br`, …) or a
   public-suffix lookup, so `co.uk`/`com.au` resolve correctly. This is more
   code and the set is inherently incomplete (three-label TLDs like
   `pvt.k12.ma.us` are not covered); the contract is harder to pin and the
   implementer must decide which TLDs to include.

Regardless of option, the normal single-label path must be unchanged:
`get_tld('https://example.com')` → `'com'`.

## Behavior
- `get_tld('https://example.com')` → `'com'` (regression guard, single-label
  still works).
- `get_tld('https://www.example.co.uk/x')` → option 1: `'uk'` (documented
  last-label, two-label limitation); option 2: `'co.uk'` (full TLD).
- `get_tld('https://intranet')` (dotless host) → `''` (no TLD) — a bare
  hostname is NOT returned as a TLD.
- `get_tld('https://localhost:8080/x')` (dotless host) → `''` (no TLD).
- `get_tld('')` → `''` (no netloc → no TLD, no crash).
- `get_tld('not-a-url')` → `''` (no netloc → no TLD, no crash).

## Guard inputs
- `get_tld('https://intranet')` → `''` (dotless host, no TLD).
- `get_tld('https://localhost:8080/x')` → `''` (dotless host with port, no
  TLD).
- `get_tld('')` → `''` (empty input, no netloc, no crash).
- `get_tld('not-a-url')` → `''` (scheme-less input, no netloc, no crash).

## Acceptance criteria
1. `get_tld('https://example.com')` → `'com'` (regression guard: single-label
   TLD still works).
2. `get_tld('https://www.example.co.uk/x')` → the chosen behavior pinned
   (option 1: `'uk'` + a clear docstring note that two-label TLDs return the
   last label; option 2: `'co.uk'`).
3. `get_tld('https://intranet')` → `''` (dotless host is NOT returned as a
   TLD).
4. `get_tld('')` and `get_tld('not-a-url')` → `''` (no netloc → no TLD, no
   crash).

## Pinning tests to add
- `test_get_tld_single_label_regression`:
  `get_tld('https://example.com') == 'com'` (single-label still works).
- `test_get_tld_two_label_documented`:
  option 1: `get_tld('https://www.example.co.uk/x') == 'uk'` (last label,
  two-label limitation documented); option 2:
  `get_tld('https://www.example.co.uk/x') == 'co.uk'` (full TLD).
- `test_get_tld_dotless_host_no_tld`:
  `get_tld('https://intranet') == ''` (bare hostname is NOT a TLD).
- `test_get_tld_dotless_host_with_port_no_tld`:
  `get_tld('https://localhost:8080/x') == ''` (dotless host with port, no TLD).
- `test_get_tld_empty_and_no_netloc`:
  `get_tld('') == ''` and `get_tld('not-a-url') == ''` (no netloc → no TLD,
  no crash).

## Docs update (same PR)
`docs/url-utils.md` — the `get_tld` entry already documents the contract hole
(ARCH-61). After the fix, update the `get_tld` entry to state the new contract
(option 1: "returns only the last dot-label; correct only for single-label
TLDs; two-label TLDs return the second-level label (documented limitation, use
a public-suffix library for the full TLD); dotless hosts return `''` (no
TLD)"; option 2: "returns the full TLD using a known-two-label-TLD set;
dotless hosts return `''`"). Remove/adjust the Contract-holes callout for this
hole once merged.
