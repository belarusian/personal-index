# TICKET-362: tags.TagStore.create_tag docstring over-promises "Create a new tag"

- File: personal_index/tags.py
- Method: TagStore.create_tag (line ~100)
- Symptom (class b, doc-drift): docstring says "Create a new tag." but the body
  `self._tags[name] = tag` is an UPSERT — re-creating a tag with the same name
  silently REPLACES the existing tag in place (color, description, created_at
  are overwritten), rather than raising or appending. Same shape as
  TICKET-360 (storage.add_interest) and TICKET-361 (interests.add).
- Evidence line: `tag = Tag(name=name, color=color, description=description)`
  followed by `self._tags[name] = tag` (dict-keyed store -> upsert).
- No existing test pins the upsert: test_create_tag (tests/test_tags.py:42)
  creates the tag once and asserts name/color only.
- Minimal additive fix: reword the docstring to state the exact upsert
  semantics ("Create a tag, or replace an existing tag with the same name."),
  and add ONE behavior test pinning the corrected claim against the observed
  store state: re-creating the same name keeps count at 1 and the returned
  object reflects the new color/description.

Issue: #562
