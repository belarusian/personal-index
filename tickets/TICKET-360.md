# TICKET-360: storage.add_interest docstring over-promises "Add a new interest" (omits update branch)

Status: RESOLVED (merged to main 0d72a9c, gh #558 closed)
Module: personal_index/storage.py
Class: (b) doc-drift

## Symptom
`Storage.add_interest` docstring (line 47) reads "Add a new interest." but the
body performs an UPSERT: if an existing interest with the same `name` is found,
it is replaced in place (lines 55-59) rather than a new interest being appended.
The docstring omits the update branch entirely.

## Evidence
- Line 47: `"""Add a new interest."""`
- Lines 55-59:
    for i, existing in enumerate(interests):
        if existing["name"] == interest.name:
            interests[i] = interest.to_dict()
            self._write_json(self.interests_file, interests)
            return interest
- Sibling `add_page` (line 115) documents the identical upsert semantics
  precisely: `"""Add or update an indexed page."""`
- Behavior already exercised by tests/test_storage.py::test_update_existing_interest
  (asserts count stays 1 and keywords are updated), but the docstring claim is
  not corrected to match.

## Minimal additive fix
Reword the docstring to state the exact upsert semantics:
"Add or update an interest (replaces an existing interest with the same name)."
Add ONE behavior test pinning the corrected claim against the returned object /
observed store state (re-adding the same name updates in place, count unchanged).

## Issue
Issue: #558
