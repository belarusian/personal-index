# TICKET-363: content_digest.DigestGenerator class docstring over-promises "indexed content"

**File:** personal_index/content_digest.py
**Symptom:** Class docstring (line 130-134) said "Generates content digests from indexed content. Groups content by topics/tags and generates formatted digest reports." but the code works with manually added DigestEntry objects via add_entry/add_entries (no index), and groups by tags OR source (or none) - not "topics/tags".
**Evidence:** Line 131: "Generates content digests from indexed content." - the __init__ method (line 137) just initializes an empty list; entries are added manually via add_entry (line 140) or add_entries (line 144). _resolve_sections (line 183) dispatches to _group_by_tags or _group_by_source.
**Fix:** Reworded the class docstring to state the exact mechanism: "Generates content digests from entries added via add_entry/add_entries. Groups entries by tags or source and generates formatted digest reports." Added ONE behavior test (TestGeneratorDocstringClaim.test_digest_contains_exactly_added_entries) pinning the corrected claim against the returned digest object.
**Status:** RESOLVED
Issue: #564
