# TICKET-437

- File: personal_index/content_changelog.py
- Function: ContentChangelog.get_entries
- Class: (b) doc-drift (blanket docstring, sub-components not enumerated)
- Symptom: docstring "Get change entries, optionally filtered by URL." does not
  enumerate the guard path (falsy url -> all entries) nor the exact-match
  semantics (e.url == url, not substring/prefix), nor that a fresh list copy is
  returned (not the internal list).
- Evidence: line 29-33 (def get_entries ... return list(self._entries)).
- Minimal additive fix: reword docstring to state the exact conditional
  (falsy url -> copy of ALL entries; truthy url -> only entries with e.url == url
  exact match) and that a new list is returned; add ONE pinning test asserting the
  RETURNED OBJECT fields for the normal filtered case AND the falsy-url guard path.
- Issue: #712
- Status: OPEN
