# TICKET-514 — Reword Exporter.manager docstring to exact contract + pinning tests

Status: RESOLVED (merged via PR #888)

## File
personal_index/export.py

## Symptom
`Exporter.manager` (line 51) carries a placeholder name-echo docstring:

    @property
    def manager(self) -> BookmarkManager:
        """Manager."""
        return self._manager

The docstring says nothing about the actual contract.

## Evidence (verified live)
- `Exporter().manager` returns a `BookmarkManager` — the SAME object as `self._manager` (not a copy).
- `Exporter(manager=m).manager is m` -> True (returns the injected reference unchanged).
- Repeated access is stable/pure: `e.manager is e.manager` -> True; no mutation.

## Exact contract
Read-only accessor returning the underlying `BookmarkManager` instance held by the
exporter — the one injected at construction, or a fresh default created in `__init__`
when none was supplied. Returns the same reference on every call (no copy, no
re-creation); pure.

## Minimal additive fix
Reword the docstring to state the exact contract above; add pinning tests
(TestExporterManager) covering: default returns a BookmarkManager, returns the same
reference as `_manager`, injected manager returned unchanged, and idempotent/pure
access.

## Issue
Issue: #887
