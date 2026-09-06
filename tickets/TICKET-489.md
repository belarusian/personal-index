# TICKET-489: ContentNormalizer.normalize docstring drift (class-(b) doc-drift)

Status: OPEN (tracker reconciliation - renumbered from the parallel run's
mislabelled "TICKET-487"; TICKET-487 on main is the pagination ticket).
Issue: #826

- File: personal_index/content_transform/normalizer.py
- Method: ContentNormalizer.normalize
- Symptom (class-(b) doc-drift): the docstring is the generic "Normalize a
  content item." / "Normalized content item." but the code does four
  specific, contract-bearing things the docstring does not state:
  1. non-destructive copy: `result = dict(content)` - the input dict is
     never mutated; a shallow copy is returned.
  2. per-flag conditional normalization: title/url/tags are each normalized
     ONLY when the corresponding `self.normalize_*` flag is set AND the key
     is present in the input.
  3. tags list-only normalization: `tags` is normalized only when it is a
     `list`; a non-list `tags` value is passed through unchanged.
  4. absent keys pass-through: keys not present in the input are left
     untouched (no key is added or removed).
- Evidence:
  - personal_index/content_transform/normalizer.py:24-48 (normalize body:
    `result = dict(content)`; `if self.normalize_titles and "title" in
    result`; `if isinstance(tags, list)`; no key added/removed).
- Minimal additive fix (deferred to a future cycle - this cycle is tracker
  reconciliation only): reword the docstring to state the four conditions
  above and add ONE pinning behavior test that returns the normalized object
  and asserts (a) the input dict is unmutated, (b) a disabled flag leaves its
  key unchanged, (c) a non-list `tags` passes through, (d) an absent key is
  not added - alongside the normal all-flags-on case.
