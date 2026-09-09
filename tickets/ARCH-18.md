# ARCH-18: Silent pattern compilation failure disables required_patterns check

- Status: IMPLEMENTED PR #1126@d109c52 (cycle 201: required_patterns compile-failure loudness + pinning test)
- Component: `personal_index/content_filter.py`
- Issue: #1052

## Symptom

`_compile_patterns` silently drops invalid regex patterns (via
`suppress(re.error)`). For `required_patterns`, if ALL provided patterns
are invalid, `self._compiled_required` is empty, check 6 in
`get_filter_reasons` is skipped entirely, and the filter silently accepts
pages that should have been rejected. The caller has no way to detect
that their required patterns were all invalid.

This is a safety gap: a single typo in a required pattern (e.g. an
unescaped `[`) silently disables the entire required-pattern check.

## Evidence