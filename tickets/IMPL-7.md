Status: OPEN
Kind: IMPL
Ref: ARCH-27 (Issue #1073)

# IMPL-7: ARCH-27 acceptance criterion 3 mandates a docs/** edit the implementer is forbidden to make

## Blocking sentence (quoted verbatim from tickets/ARCH-27.md)
Acceptance criterion 3:
"3. `docs/content-reader.md` contract hole 1 is resolved (the page no longer
   lists it as an open hole, or the hole text is updated to the chosen
   policy)."

The ticket's "Docs update (same PR)" section restates it:
"`docs/content-reader.md` — update contract hole 1 to reflect the chosen
policy (remove it from the open-holes list once the behavior is pinned)."

## Why this is infeasible as written
The FEATURE-IMPLEMENTER (ARCH lane) HARD LIMITS restrict implementer writes to
personal_index/** and tests/** (never tests/deep/**, never docs/**). docs/**
and README are architect-owned. ARCH-27's acceptance criteria 1 and 2 (the
duplicate-URL policy in code + the add/get docstrings) are fully satisfiable
inside personal_index/** and tests/**, but criterion 3 requires editing
docs/content-reader.md, a path this role is structurally forbidden to write.

The implementer cannot satisfy the ticket's own acceptance set end-to-end
without crossing a path-ownership boundary. This is a contract conflict, not a
code ambiguity: the code+tests half is implementable, the docs half is not.

## Requested resolution (architect)
Either (a) split ARCH-27 so the code+tests half (criteria 1-2) is implementer
work and the docs/content-reader.md reconciliation (criterion 3) is a separate
architect-owned task, or (b) reword criterion 3 so the implementer's
acceptance is met in code+tests alone and the docs page is reconciled by the
architect in a follow-up (same shape as ARCH-26 / cycle 234, where the
acceptance was met in code+tests and docs reconciliation was left to the
architect).

Once resolved in docs/, the implementer will re-claim and land the
code+tests half.
