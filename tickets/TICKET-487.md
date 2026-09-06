# TICKET-487: ContentNormalizer.normalize docstring drift (class-(b))

- **File:** personal_index/content_transform/normalizer.py
- **Method:** ContentNormalizer.normalize (lines ~24-49)
- **Symptom:** Docstring is generic "Normalize a content item." but code implements specific contract-bearing behaviors not documented:
  1. NON-DESTRUCTIVE: copies input via `result = dict(content)` and returns new dict; caller input unchanged.
  2. CONDITIONAL per-flag + per-key: title normalized only if `normalize_titles` and key present; url only if `normalize_urls` and key present; tags only if `normalize_tags` and key present.
  3. tags normalized element-wise ONLY when value is list; non-list tags left untouched (no crash/coercion).
  4. Absent keys passed through unchanged.
- **Evidence:** `sed -n '24,49p'` shows copy, conditional checks, isinstance(tags,list) guard.
- **Verified behavior:**
  - normalize({'title':'  hello world  ','url':'  https://X.com  ','tags':[' A ','b ']}) -> {'title':'Hello World','url':'https://X.com','tags':['a','b']}
  - input dict unchanged after call
  - normalize({'foo':'bar'}) -> {'foo':'bar'}
  - normalize({'tags':'notalist'}) -> {'tags':'notalist'}
  - with normalize_titles=False, title left as-is
- **Minimal additive fix:** Reword normalize docstring to state the four behaviors above; add pinning test class TestNormalizePinning in tests/test_content_transform.py covering full-item, non-destructive, absent-keys, non-list-tags, flag-off cases.
Status: OPEN
Issue: #826
