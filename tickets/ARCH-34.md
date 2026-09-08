# ARCH-34: content_merger — `strategy` is never validated, so an unrecognized strategy silently runs `concatenate` and `merge_strategy` hides the typo

Status: OPEN
Component: `personal_index/content_merger.py`
Issue: #1095
Refs: ARCH-2 (#983 umbrella)

## Symptom

`ContentMerger.__init__(strategy: str = "concatenate")` stores the string
verbatim with **no validation** against the four documented strategies
(`concatenate`, `longest`, `highest_priority`, `unique_paragraphs`). In
`merge()`, the dispatch is an `if/elif/elif/else` chain whose **`else` branch
is the `concatenate` fallback** — so *any* string that is not exactly one of
the three named strategies (e.g. `"longst"`, `"CONCATENATE"`,
`"highest-priority"`, `""`) silently executes `_merge_concatenate`.

The consequence is a two-part silent failure:

- **Wrong behavior, no error**: a caller who misspells a strategy (or passes
  a case-variant) gets concatenated output with no exception, no warning, and
  no way to detect the mistake from the call site.
- **The result field hides the typo**: `MergedContent.merge_strategy` is set
  to the **executed** branch name (`"concatenate"`), **not** the requested
  value. So a caller who asked for `"longst"` reads back
  `merge_strategy == "concatenate"` and has no signal that their requested
  strategy was never honored. The field reports what *happened*, not what was
  *asked for*, so it cannot be used to verify the caller's intent.

This is the single most important hole in the module: it is the only place
where a plausible caller input produces a **silently wrong result with a
self-contradicting field**. Every other behavior (empty guard, priority sort,
tag normalization, metadata first-writer-wins) is at least internally
consistent.

## Evidence

- `personal_index/content_merger.py` line 69:
  `def __init__(self, strategy: str = "concatenate"):` — stores
  `self.strategy = strategy` (line 70) with no validation.
- `personal_index/content_merger.py` lines 92-101: the dispatch chain
  `if self.strategy == "longest" / elif "highest_priority" / elif
  "unique_paragraphs" / else: return self._merge_concatenate(...)` — the
  `else` is the silent fallback for any unrecognized string.
- `personal_index/content_merger.py` line 131 (in `_merge_concatenate`):
  `merge_strategy="concatenate"` — the field is set to the executed branch
  name, not the requested `self.strategy`.
- `MergedContent` dataclass (lines 35-57): `merge_strategy: str =
  "concatenate"` — a result field a caller would naturally read to confirm
  which strategy ran.

## Minimal additive fix

Pick ONE of the two, and make the strategy contract explicit:

**Option A (validate at construction)**: in `__init__`, raise `ValueError`
for any `strategy` not in the four documented names, and reword the
`__init__` docstring to state the accepted set. `merge()`'s `else` branch
then becomes unreachable for a valid instance.

**Option B (report the requested value)**: keep the lenient fallback but set
`MergedContent.merge_strategy` to the **requested** `self.strategy` (or add a
separate field) so a caller can detect that an unrecognized strategy fell
through to `concatenate`, and reword the `merge` docstring to state the
fallback explicitly.

The contract decision is: a caller must not be able to silently receive
concatenated output for a strategy they did not request, while the result
field reports a strategy they did not ask for.

## Acceptance criteria

- An unrecognized `strategy` either raises at construction (Option A) or is
  detectable from the returned `MergedContent` (Option B) — never both silent.
- The `merge_strategy` field (or a new field) reflects the caller's intent,
  not only the executed branch.
- The `__init__` and `merge` docstrings state the accepted strategy set and
  the fallback behavior exactly.

## Pinning tests to add

- **Unrecognized strategy falls through (the hole)**: `ContentMerger(strategy="longst").merge([s1, s2])`
  with distinct non-empty content returns `content` equal to the `concatenate`
  output and `merge_strategy == "concatenate"` — pinning the silent fallback
  and the field that hides the requested value.
- **Guard path (empty input)**: `ContentMerger().merge([])` returns `None`.
