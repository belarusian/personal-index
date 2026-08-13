# TICKET-001: Refactor cli_verify.verify (191 lines) into sub-functions

**File:** `personal_index/cli_verify.py`  
**Function:** `verify` (lines 19–212)  
**Lines:** 191  
**Severity:** Medium

## Evidence

The `verify` function is a Click command handler that performs 6 distinct verification checks plus a full pipeline self-test, all inlined as sequential blocks:

- Lines 38–48: `check()` helper closure
- Lines 50–60: Check 1 — Data directory writable
- Lines 62–73: Check 2 — Interest store works
- Lines 75–86: Check 3 — Tag store works
- Lines 88–104: Check 4 — Search index works
- Lines 106–117: Check 5 — Content filter works
- Lines 119–130: Check 6 — Content scorer works
- Lines 133–191: Full pipeline self-test (skip with --quick)
- Lines 193–212: Cleanup and summary

## Impact

- Single point of failure: any change to one check risks the others
- Diff readability: changes to any check produce a 191-line diff
- No individual check can be unit-tested in isolation

## Suggestion

Extract each check into a private method:
