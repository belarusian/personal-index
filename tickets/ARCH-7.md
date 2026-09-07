Status: OPEN
Kind: ARCH
Author: architect (cycle 172)
Issue: #1001

# ARCH-7: `ContentCategorizer.MIN_TOPIC_SCORE` dead class constant

## Component
`personal_index.content_categorizer.ContentCategorizer`
(content_categorizer.py, line 269).

## Symptom
`MIN_TOPIC_SCORE: float = 0.1` is declared as a class-level constant but is
never read anywhere in the module or the repo (verified: the only occurrence
in `personal_index/`, `tests/`, and `docs/` is its own definition at line
269). The actual score threshold is the instance attribute `self.min_score`,
set from the `min_score` constructor argument (default `0.1`) and used in
`_score_all_topics` (`if score >= self.min_score`). A reader of the class
would reasonably assume `MIN_TOPIC_SCORE` is the threshold constant, but it
is dead — the two values happen to coincide only because the constructor
default equals the constant. This is a genuine class-(b) contract hole: a
public-looking constant that does nothing.

## Public contract (the code is the truth)
- `ContentCategorizer.MIN_TOPIC_SCORE` is **not** referenced by any code path.
  The threshold that gates topic inclusion is `self.min_score` (instance
  attribute, set in `__init__` from the `min_score` arg, default `0.1`).
- `_score_all_topics` keeps a topic only when `score >= self.min_score`.

## Acceptance criteria
- `MIN_TOPIC_SCORE` is removed (it is dead), OR — if the operator prefers to
  keep a module-level default — it is renamed to make clear it is a default
  (e.g. `DEFAULT_MIN_SCORE`) and `__init__`'s `min_score` default is
  documented as derived from it. Either way, the docs page
  `docs/content-categorizer.md` "Module constants" entry for
  `MIN_TOPIC_SCORE` is updated to match the chosen resolution (remove the
  entry, or reword it to state it is a default, not the live threshold).
- The live threshold `self.min_score` is the single source of truth for the
  inclusion gate; no code path reads a class-level constant for it.

## Pinning tests to add
`test_min_score_threshold_pinned` — construct a `ContentCategorizer` with a
non-default `min_score` (e.g. `0.5`) and a text that yields a topic score
between the default `0.1` and `0.5`; assert the topic is EXCLUDED (proving
the gate reads `self.min_score`, not a fixed `0.1` constant). Alongside, a
normal case with the default `min_score` asserting the same topic IS
included — one test pins both the live-threshold behavior and the guard
(exclusion) path.

## Docs page it updates
`docs/content-categorizer.md` (the "Module constants" `MIN_TOPIC_SCORE`
entry + the contract-holes line, which this ticket resolves).
