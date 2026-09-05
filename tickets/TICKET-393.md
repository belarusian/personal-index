# TICKET-393

**Status:** OPEN
**File:** personal_index/cli_verify.py
**Symptom:** `_check_full_pipeline` docstring is a placeholder ("Run a full pipeline self-test.") that does not enumerate the exact sub-components the body performs.
**Evidence:** Line 263: `"""Run a full pipeline self-test."""` — body calls `_create_test_content`, `_setup_mini_pipeline`, `_create_test_page`, `_verify_filter`, `_run_score`, `_run_tag_index`, and returns `(passed, error)` tuple.
**Fix:** Reword docstring to enumerate exact sub-components; add ONE pinning behavior test asserting on the returned `(passed, error)` tuple (success: `(True, "")`, failure: `(False, <non-empty reason>)`).

Issue: #624
