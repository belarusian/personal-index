# TICKET-455: Annotation.add_tag / remove_tag docstrings omit dedup guard + updated_at side effect

- File: personal_index/content_annotations.py
- Symptom: class-(b) doc-drift. `Annotation.add_tag` docstring was the blanket
  "Add a tag to this annotation." while the body (a) appends the tag ONLY when
  it is not already present (`if tag not in self.tags`) and (b) sets
  `self.updated_at` to the current UTC ISO-8601 timestamp on EVERY call,
  whether or not the tag was newly added. `Annotation.remove_tag` had the
  mirror-image drift ("Remove a tag from this annotation." vs. the
  `if tag in self.tags` guard + the same `updated_at` side effect).
- Evidence: add_tag / remove_tag bodies (lines ~43-54).
- Minimal additive fix: reword both docstrings to state the exact conditional
  (dedup / no-op guard) and the `updated_at` side effect; add ONE behavior test
  (test_add_tag_dedup_guard_and_updated_at) pinning the corrected claim against
  the returned object, including the guard-path (duplicate-tag) input alongside
  the normal case.
- Issue: #<n>
