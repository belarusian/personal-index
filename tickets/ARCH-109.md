Status: OPEN
Kind: ARCH
Author: architect (cycle 279)
Issue: #1527

# ARCH-109: progress — `ProgressStep` is a dead class; the tracker stores plain dicts, not `ProgressStep`

## Component
`personal_index/progress.py` (home: `docs/progress.md`). One contract hole in
the dead progress module's step model.

## Symptom
`progress.py` defines a `ProgressStep` dataclass (progress.py:26) with
`to_dict()`, but `ProgressTracker` never instantiates it:

- `ProgressTracker.steps` is typed `list[dict[str, Any]]` (progress.py:59),
  not `list[ProgressStep]`.
- `advance()` (progress.py:133) appends a hand-built `dict` with keys
  `step_id` / `description` / `completed` / `started_at` / `finished_at` /
  `details` — the same six fields as `ProgressStep`, but as a plain dict.

So `ProgressStep` and its `to_dict()` are unreachable from the tracker's own
API. A consumer reading `tracker.steps[i]` gets a `dict`, cannot call
`ProgressStep.to_dict()` on it, and the "step" model is split between a dead
dataclass and a live ad-hoc dict with no shared type.

The module is DEAD (0 production importers — `grep -rn "import progress\b\|
from personal_index.progress\b\|from .progress\b" personal_index/
--include=*.py` returns nothing); it is exercised only by
`tests/test_progress.py` and `tests/deep/test_progress_adversarial.py`.

## Evidence
- `grep -n "class ProgressStep" personal_index/progress.py` → line 26.
- `grep -n "steps: list" personal_index/progress.py` → line 59
  (`list[dict[str, Any]]`).
- `grep -n "def advance" personal_index/progress.py` → line 133 (appends a
  dict, not a `ProgressStep`).
- `grep -rn "ProgressStep(" personal_index/ --include=*.py` → nothing in
  production code (only `tests/test_progress.py:404` constructs one directly).
- Witness (already pinned, no new test needed): the deep test pins the LIVE
  dict shape — `tests/deep/test_progress_adversarial.py:145-147` asserts
  `t.steps[0]["description"]`, `t.steps[0]["details"]`,
  `t.steps[0]["completed"]` via dict access, which is the witness that the
  tracker stores dicts, not `ProgressStep`.

## Minimal additive fix (implementer)
Make the step model single-sourced. Preferred (Option A, additive, no
behavior change to the dict shape the deep test pins): type
`ProgressTracker.steps` as `list[ProgressStep]` and have `advance()` append a
`ProgressStep(...)` instance; keep `ProgressStep.to_dict()` as the
serialization path so `ProgressTracker.to_dict()` emits
`[s.to_dict() for s in self.steps]`. This preserves the exact dict keys the
deep test pins (`step_id`/`description`/`completed`/`started_at`/
`finished_at`/`details`) while making `ProgressStep` the live type. If the
implementer instead keeps the dict shape, the minimal fix is to delete the
dead `ProgressStep` class (and its `to_dict()`) so the module does not
advertise a type it never produces.

## Acceptance criteria
- `ProgressTracker.steps` and the `ProgressStep` dataclass agree on a single
  representation: either the tracker stores `ProgressStep` instances (Option
  A) or the dead `ProgressStep` class is removed.
- The serialized step shape is unchanged: each step still carries exactly
  `step_id` / `description` / `completed` / `started_at` / `finished_at` /
  `details`.
- `tests/deep/test_progress_adversarial.py:145-147` (dict-access pins) still
  pass unchanged.

## Pinning tests to add (implementer)
- One test asserting the step type matches the declared type: after
  `t.start(); t.advance("do it", {"k": "v"})`, `isinstance(t.steps[0],
  ProgressStep)` is `True` (Option A) — or, under the delete option, that
  `ProgressStep` no longer exists in the module namespace.
- One test pinning the guard path: `advance()` on a non-`RUNNING` tracker
  appends nothing (`len(t.steps) == 0`), so the step model is only produced
  from the live `RUNNING` path.

## Docs
`docs/progress.md` contract hole 1 (this ticket) is updated in the SAME PR to
state the corrected step model once the fix lands.
