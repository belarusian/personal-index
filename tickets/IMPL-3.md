Status: CLOSED (resolved by architect cycle 177: docs/content-categorizer.md corrected, ARCH-7 closed)
Kind: IMPL
Author: implementer (cycle 173)
References: ARCH-7 (issue #1001)

# IMPL-3: ARCH-7 docs/** criterion is out of the implementer's path

## Blocking sentence (quoted verbatim from tickets/ARCH-7.md)

Acceptance criteria:
"`MIN_TOPIC_SCORE` is removed (it is dead), OR — if the operator prefers to
keep a module-level default — it is renamed to make clear it is a default
(e.g. `DEFAULT_MIN_SCORE`) and `__init__`'s `min_score` default is
documented as derived from it. Either way, the docs page
`docs/content-categorizer.md` "Module constants" entry for
`MIN_TOPIC_SCORE` is updated to match the chosen resolution (remove the
entry, or reword it to state it is a default, not the live threshold)."

Docs page it updates:
"`docs/content-categorizer.md` (the "Module constants" `MIN_TOPIC_SCORE`
entry + the contract-holes line, which this ticket resolves)."

## Why this blocks the implementer

ARCH-7 has two acceptance criteria. The implementer completed the one that
falls in the implementer's path (personal_index/** and tests/**):

- `personal_index/content_categorizer.py`: the dead class constant
  `MIN_TOPIC_SCORE: float = 0.1` (line 269) is removed. It was never read
  anywhere in the module or the repo; the live inclusion gate is the instance
  attribute `self.min_score` (set in `__init__` from the `min_score` arg,
  default `0.1`), used in `_score_all_topics` (`if score >= self.min_score`).
- `tests/test_content_categorizer.py` gained `test_min_score_threshold_pinned`,
  asserting the RETURNED topic set for BOTH the normal case (default
  `min_score=0.1` includes a 0.15-scoring topic) AND the guard case
  (`min_score=0.5` excludes the same topic) — proving the gate reads
  `self.min_score`, not a fixed 0.1 class constant.

The remaining criterion is a docs/** edit:
- `docs/content-categorizer.md` "Module constants" entry for
  `MIN_TOPIC_SCORE` (line 17): remove the entry (the constant no longer
  exists) or reword it to state it is a default, not the live threshold.
- `docs/content-categorizer.md` "Contract holes" line (line 125): the
  `MIN_TOPIC_SCORE` dead-constant hole is resolved by the code change; the
  line must be updated/removed to match.

Per the COORDINATION role split, docs/** is the architect's single-writer path
("docs/** and README = architect only"). The implementer is forbidden from
editing docs/**, so this criterion cannot be satisfied by this role. It is
pushed back to the architect rather than deviated from.

## Requested resolution (architect)

Apply the docs/** edits named above so `docs/content-categorizer.md` matches
the code (the `MIN_TOPIC_SCORE` constant is removed; `self.min_score` is the
single source of truth for the inclusion gate), then re-run ARCH-7's
acceptance criteria and CLOSE it. The code portion is already merged on main
(see ARCH-7 status).
