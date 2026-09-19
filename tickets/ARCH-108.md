# ARCH-108 — versioning.py `VersionTracker` keeps versions only in memory (url-keyed, no persistence) and offers no rollback/delete-by-id, diverging from the live twin's JSON-backed item_id-keyed contract

- **Status:** CLOSED (architect close, cycle 319; was VERIFIED (validator cycle 271 @ main 76e12b6; Option (b) confirmed: VersionTracker docstring at versioning.py:51-68 documents in-memory/url-keyed divergence, no storage_path/_save/rollback_to/delete_version; pinning tests tests/test_versioning.py 32 passed; adversarial: no storage_path/_save attrs; [was IMPLEMENTED #1588@449a294 impl336 cycle 337 Option b]))
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** personal_index/versioning.py (DEAD module — 0 importers; see docs/versioning.md) + personal_index/content_versioning.py (the live JSON-backed, item_id-keyed twin it was meant to mirror)
- **Issue:** #1526 (ARCH-108, left OPEN as the implementer claim queue — no `Closes` in PR body)

## Symptom

`versioning.py` is a dead parallel implementation of the content-versioning
system: it is never imported anywhere in `personal_index/` (witness below), and
it is an **in-memory, url-keyed** tracker (`VersionTracker` + a bare
`ContentVersion` dataclass, no persistence) where the live twin
`content_versioning.py` is a **JSON-file-backed, item_id-keyed** engine
(`ContentVersioning` + `create_version`/`get_versions`/`get_version`/
`delete_version`/`rollback_to`/`clear_versions` + `_load`/`_save`). The two
modules share the class name `ContentVersion` and the method name
`get_versions` but their contracts have silently diverged.

The concrete, verifiable holes are two:

1. **In-memory only — no persistence.** The dead module's `VersionTracker`
   (versioning.py:49) stores everything in a process-local
   `dict[str, list[ContentVersion]]` keyed by **url** (versioning.py:53). There
   is no `storage_path`, no `_load`, and no `_save` anywhere in the module —
   nothing survives a process restart, and a fresh `VersionTracker()` always
   starts empty. The live twin's `ContentVersioning` (content_versioning.py:31)
   persists to `versions.json` via `_load` (content_versioning.py:46) and
   `_save` (content_versioning.py:83), so its history survives across
   constructions and processes.

2. **No rollback / no delete-by-id.** The dead module's only removal operations
   are `clear(url)` (drop one url's whole history) and `clear()` (drop
   everything) (versioning.py:124). There is no `rollback_to` and no
   `delete_version` — a single version cannot be removed or restored. The live
   twin offers `delete_version` (content_versioning.py:174) and `rollback_to`
   (content_versioning.py:195). A consumer mirroring the live contract
   (persisted history, rollback, delete-by-id) cannot do so against the dead
   module.

This is the dead-module + divergent-contract class (ARCH-100/102/105/106/107
pattern): the module ships a public versioning API whose contract (persisted
history + rollback + delete-by-id) it does not fulfill, and which is
incompatible with the live twin it was meant to mirror.

## Evidence (file:line)

DEAD-MODULE witness:
- `grep -rn 'import versioning\|from personal_index.versioning\|from .versioning'
  personal_index/ --include=*.py` returns **nothing** (rc=1) — versioning.py is
  never wired.
- Its only consumer is the test suite: `tests/test_versioning.py`
  (`from personal_index.versioning import ...`).

Dead-module in-memory store (no persistence):
- personal_index/versioning.py:52-54 — `VersionTracker.__init__` sets only
  `self._versions: dict[str, list[ContentVersion]] = {}` (keyed by **url**) and
  `self._max_versions = max_versions`; **no `storage_path`, no `_load()` call**.
- No `_load`/`_save`/`storage_path`/`open(`/`json` anywhere in the module
  (imports are `hashlib`, `logging`, `dataclasses`, `datetime`).
- personal_index/versioning.py:99 — `def get_versions(self, url)` reads from the
  in-memory dict only.

Dead-module removal surface (no rollback / no delete-by-id):
- personal_index/versioning.py:124 — `def clear(self, url=None)` is the ONLY
  removal method (pops one url's list or clears all).
- No `rollback_to` and no `delete_version` method exists anywhere in the module.

Live-twin persistence + rollback/delete — the contract the dead module diverges
from:
- personal_index/content_versioning.py:31 — `class ContentVersioning:`.
- personal_index/content_versioning.py:34 — `__init__(self, storage_path=None)`
  (a `storage_path` the dead module has no analogue of).
- personal_index/content_versioning.py:46 — `def _load(self)`.
- personal_index/content_versioning.py:83 — `def _save(self)`.
- personal_index/content_versioning.py:174 — `def delete_version(self, item_id, version_id) -> bool:`.
- personal_index/content_versioning.py:195 — `def rollback_to(self, item_id, version_id) -> bool:`.
- personal_index/content_versioning.py:147 — `def get_versions(self, item_id)`
  (keyed by **item_id**, not url).

## Proposed fix (implementer)

Two acceptable resolutions; pick one and record it in the ticket:

(a) **Align the dead module to the live twin's contract** (preferred if the
    module is ever revived): add a `storage_path` + `_load`/`_save` persistence
    pair to `VersionTracker` (versioning.py:49) so history survives a restart,
    and add `rollback_to`/`delete_version` mirroring the live twin — so the
    module offers persisted history, rollback, and delete-by-id.

(b) **Explicitly defer / document the divergence** (if the module stays dead):
    keep the store in-memory and url-keyed, but state in the `VersionTracker`
    docstring and in docs/versioning.md that the store is **in-memory only**
    (nothing survives a restart) and that there is **no `rollback_to`/
    `delete_version`** — and that this is intentionally NOT the live twin's
    JSON-backed, item_id-keyed, rollback/delete contract — so a future reader
    does not assume the two are interchangeable.

Either way, the docs/versioning.md "Known contract holes" entry must reflect the
chosen resolution.

## Acceptance criteria

- [ ] The dead-module status (0 importers) is stated in docs/versioning.md
      header (done in this PR) and in this ticket.
- [ ] The near-name distinction from `content_versioning.py` is stated in the
      page header (done in this PR).
- [ ] The in-memory/no-persistence + no-rollback/no-delete divergences are
      pinned with file:line evidence (above).
- [x] A resolution (a) or (b) is chosen and the docs page updated to match. (Option (b) — chosen by the architect in cycle 297 and confirmed on main; the docs page already reflects it. This IMPL pass keeps the module, documents the divergence in the VersionTracker docstring, and pins it.)
- [x] Pinning test (implementer, tests/** — NOT the architect's path): one
      behavior test that constructs a `VersionTracker`, records a version, and
      asserts the persistence/rollback contract the chosen resolution states —
      for (a) assert a fresh `VersionTracker` reloads the recorded version from
      disk and that `rollback_to`/`delete_version` exist and work; for (b)
      assert a fresh `VersionTracker()` starts empty (nothing persisted) and
      that no `rollback_to`/`delete_version`/`_save`/`storage_path` attribute
      exists, pinning the documented divergence. (DONE: `TestVersionTrackerInMemoryDivergence` in tests/test_versioning.py.)

## Resolution (implementer, cycle 336)

**Option (b) — explicitly defer / document the divergence.** Chosen by the
architect in cycle 297 (confirmed on main) and implemented here. The dead
module `personal_index/versioning.py` is **kept** (not deleted): deleting it
would break the validator-owned deep test
`tests/deep/test_versioning_adversarial.py` (which imports `ContentVersion` /
`VersionTracker` from it) and fail the gate. The live twin
`content_versioning.py` is the **sole** content-versioning contract.

What this pass changed:
- `personal_index/versioning.py` — `VersionTracker` docstring now states the
  in-memory-only, url-keyed, no-persistence, no-`rollback_to`/no-`delete_version`
  contract and that it is intentionally NOT the live twin's JSON-backed,
  item_id-keyed, rollback/delete contract (near-name disambiguation included).
- `tests/test_versioning.py` — added `TestVersionTrackerInMemoryDivergence`
  (Option (b) pinning test): a fresh `VersionTracker()` starts empty (nothing
  persisted/reloaded across constructions) and exposes no
  `storage_path`/`_save`/`_load`/`rollback_to`/`delete_version`.
- `personal_index/content_versioning.py` — **unchanged** (live module, out of
  scope).

DEFERRED to the architect (docs/**, architect-owned): any further
docs/versioning.md wording. The docs page already reflects Option (b) from
cycle 297, so no docs change is required in this IMPL pass.

## Self-review checklist (architect)

- [x] Component + public contract (signature, behavior, error paths, guard
      inputs) stated.
- [x] Acceptance criteria present.
- [x] Pinning test specified (implementer's to write; architect never writes
      tests/**).
- [x] Matching docs/versioning.md update shipped in the SAME PR.
- [x] DEAD-MODULE witness (0 importers) recorded.
- [x] Near-name-collision disambiguation (versioning vs content_versioning)
      recorded.
- [x] No personal_index/** or tests/** written by the architect.
