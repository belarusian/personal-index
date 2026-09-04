# TICKET-361: interests.InterestStore.add doc drift (omits update branch)

- File: personal_index/interests.py
- Symptom: `add` docstring says "Add an interest." but the body performs an
  UPSERT — `self._interests[interest.name] = interest` replaces an existing
  interest with the same name in place rather than appending a new one.
- Evidence line: interests.py:51-53
    def add(self, interest: Interest) -> None:
        """Add an interest."""
        self._interests[interest.name] = interest
  No existing test pins the upsert (test_add_interest adds once;
  test_add_multiple adds two distinct names).
- Minimal additive fix: reword the docstring to state the exact upsert
  semantics ("Add or update an interest (replaces an existing interest with
  the same name).") and add ONE behavior test pinning the corrected claim
  against the returned/observed store state (re-adding the same name keeps
  count at 1 and reflects the update).
- Status: OPEN
- Issue: #560
