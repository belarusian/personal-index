# ARCH-45: content-priority — from_score and _level_for_score are two divergent score→level paths

Status: OPEN
Component: `personal_index/content_priority.py`
Issue: #1129
Refs: ARCH-2 (#983 umbrella)

## Symptom

The module exposes TWO independent public ways to convert a score to a
`PriorityLevel`, and they are not equivalent:

- `PriorityLevel.from_score(score)` (lines 23-35) uses **hardcoded** bands and
  returns `LOW` for any `score > 0` (strictly greater than zero):
  `score >= 0.8` → CRITICAL, `>= 0.6` → HIGH, `>= 0.4` → MEDIUM, `score > 0`
  → LOW, else ARCHIVE. It does NOT read `PriorityConfig`.
- `PriorityCalculator._level_for_score(score)` (lines 178-189) uses the
  **config** thresholds and returns `LOW` only for `score >= low_threshold`
  (default `0.2`): `score >= critical_threshold` → CRITICAL, `>=
  high_threshold` → HIGH, `>= medium_threshold` → MEDIUM, `>= low_threshold`
  → LOW, else ARCHIVE. All four boundaries are inclusive.

For any score in `(0, 0.2)` the two paths DISAGREE: `from_score` → `LOW`,
`_level_for_score` → `ARCHIVE`. And because `from_score` ignores
`PriorityConfig` entirely, a caller who tunes `low_threshold` (or any
threshold) in the config has NO effect on `from_score`. The contract never
states which path is authoritative, or that the two are meant to differ, so an
implementer or caller cannot tell whether `from_score` is a standalone
convenience or a second (drifted) implementation of the same mapping.

This is an underspecified semantic, not a boundary nit: the two public entry
points to "score → level" can return different levels for the same score.

## Public contract (the fix must preserve the happy path)

- `calculate` / `batch_calculate` / `get_summary` keep their current
  signatures and behavior (weighted total via `_weighted_total`, `priority =
  _level_for_score(total)`, `batch_calculate` sorted by score descending,
  `get_summary` omitting absent levels).
- The score→level relationship must be made explicit (pick one and document it
  in the `from_score` docstring + `docs/content-priority.md`):
  - **Option A (single source of truth):** route `from_score` through the same
    band logic driven by the default `PriorityConfig` thresholds, so both
    paths agree for the default config and the `> 0` / `>= 0.2` LOW boundary
    is reconciled to one rule.
  - **Option B (documented divergence):** state that `from_score` is a
    standalone convenience with its own fixed bands (independent of
    `PriorityConfig`) and that `_level_for_score` is the config-driven path
    used by `calculate`/`batch_calculate`, and pin the exact boundary values
    of each so the disagreement is intentional and witnessed.
- Whichever option is chosen, the postcondition must hold and be stated: for
  any given score, the level returned by `from_score` and the level returned
  by `_level_for_score` under the default config are either identical, or the
  documented divergence is exact and pinned.

## Acceptance criteria

1. The happy path is unchanged: `calculate`/`batch_calculate`/`get_summary`
   behave exactly as documented in `docs/content-priority.md`.
2. The score→level relationship is stated in the `from_score` docstring and in
   `docs/content-priority.md` (Option A: both paths agree under the default
   config; Option B: the divergence is exact and pinned).
3. For every score in the pinned test set, `from_score(s)` and
   `_level_for_score(s)` (default config) return the documented relationship
   (identical, or the documented divergence).
4. Tuning a `PriorityConfig` threshold has the documented effect on
   `_level_for_score` and the documented (or no) effect on `from_score`.

## Pinning tests to add (tests/test_content_priority.py)

- `test_from_score_bands` — pin `from_score` at the exact boundaries:
  `0.0` → ARCHIVE, `0.1` → LOW, `0.2` → LOW, `0.4` → MEDIUM, `0.6` → HIGH,
  `0.8` → CRITICAL, and a negative score → ARCHIVE (the `score > 0` LOW
  boundary and the `score <= 0` ARCHIVE boundary).
- `test_level_for_score_bands_default_config` — pin `_level_for_score` (via a
  `PriorityCalculator` with the default config) at the exact boundaries:
  `0.1` → ARCHIVE, `0.2` → LOW, `0.4` → MEDIUM, `0.6` → HIGH, `0.8` →
  CRITICAL (the `>= low_threshold` LOW boundary, distinct from `from_score`'s
  `> 0`).
- `test_from_score_vs_level_for_score_divergence` — for a score in `(0, 0.2)`
  (e.g. `0.1`), assert the documented relationship between
  `PriorityLevel.from_score(0.1)` and
  `PriorityCalculator().calculate(...)`'s resulting level /
  `_level_for_score(0.1)` (identical under Option A, or the pinned divergence
  under Option B) — this single test pins the whole contract hole.
- `test_from_score_ignores_config` (Option B only) — construct a
  `PriorityCalculator` with a custom `low_threshold` (e.g. `0.5`) and assert
  `PriorityLevel.from_score(0.3)` is unchanged by the config, while
  `_level_for_score(0.3)` reflects the tuned threshold.

## Docs update (same PR)

`docs/content-priority.md` "Contract Holes" section (already authored in this
PR) names this as the primary hole; the implementer must update the
`from_score` and `_level_for_score` entries in the "Public API" section to
state the chosen score→level relationship once implemented.
