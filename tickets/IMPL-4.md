Status: OPEN
Kind: IMPL
Author: implementer (cycle 176)
References: ARCH-10 (issue #1015)

# IMPL-4: ARCH-10 premise is factually wrong — two distinct PipelineStats classes

## Blocking sentences (quoted verbatim from tickets/ARCH-10.md)

Symptom:
"So any `personal-index pipeline` run that reaches the stats print (i.e. every
successful run) raises `AttributeError: 'PipelineStats' object has no
attribute 'pages_filtered_in'`."

Acceptance criteria (first bullet):
"`_print_pipeline_stats` reads `stats.pages_passed_filter` (not
`pages_filtered_in`) for the 'Filtered in:' line."

## Why this blocks the implementer

ARCH-10 asserts that `PipelineStats` has no `pages_filtered_in` field and that
the field is `pages_passed_filter` (models.py line 473), and that the fix is to
make `_print_pipeline_stats` read `stats.pages_passed_filter`. That premise is
factually wrong, because there are TWO distinct `PipelineStats` dataclasses in
the codebase, and the ticket conflates them:

1. `personal_index.models.PipelineStats` (models.py line 461) — fields include
   `pages_passed_filter` (line 487) and NO `pages_filtered_in`.
2. `personal_index.pipeline_runner.PipelineStats` (pipeline_runner.py line 25)
   — fields include `pages_filtered_in` (line 30) and NO `pages_passed_filter`.

The object that `_print_pipeline_stats` actually receives is the
`pipeline_runner.PipelineStats` instance, not the `models.PipelineStats`
instance. In `cli.py` the `pipeline` command builds the runner via
`_create_pipeline_runner` (which imports `PipelineRunner` from
`personal_index.pipeline_runner`) and then calls `stats = runner.run(...)` or
`stats = runner.run_from_files(...)` (cli.py lines 703-707). Both `run` and
`run_from_files` are annotated `-> PipelineStats` and construct the
module-local `pipeline_runner.PipelineStats` (pipeline_runner.py lines 286,
296, 312, 326). That class HAS `pages_filtered_in` and does NOT have
`pages_passed_filter`.

Empirical verification (run on main f237be1):
- `hasattr(pipeline_runner.PipelineStats, 'pages_filtered_in')` is True.
- `hasattr(pipeline_runner.PipelineStats, 'pages_passed_filter')` is False.
- Calling `_print_pipeline_stats(pipeline_runner.PipelineStats(pages_crawled=1,
  pages_filtered_in=2, pages_filtered_out=3, elapsed_seconds=1.5))` prints the
  full stats block including "Filtered in:  2" and raises NO AttributeError.

So the described defect (AttributeError on every successful run) does not
exist: the current code at cli.py line 632 reads `stats.pages_filtered_in`,
which is a valid field on the object it actually receives.

## Why the proposed fix is infeasible as specified

Applying the acceptance criterion literally — change line 632 to read
`stats.pages_passed_filter` — would INTRODUCE the AttributeError the ticket
claims to remove, because the object passed at runtime
(`pipeline_runner.PipelineStats`) has no `pages_passed_filter` attribute. The
ticket's own pinning test would still pass in isolation only if the test
imports `models.PipelineStats` (which does have `pages_passed_filter`), but
that is not the class the CLI passes, so the test would pin a type the live
path never uses while breaking the live path.

## What the architect needs to decide

The ticket must be re-scoped against the correct class. Options:
(a) If the intent is that the CLI should consume `models.PipelineStats`, the
    pipeline runner must be changed to return `models.PipelineStats` (a
    cross-module contract change touching `pipeline_runner.py` and every test
    that constructs `pipeline_runner.PipelineStats(pages_filtered_in=...)`),
    which is a much larger change than ARCH-10 describes.
(b) If the intent is only to reconcile the two classes' field naming
    (`pages_filtered_in` vs `pages_passed_filter`), that is a naming-unification
    decision the architect must make explicit, not a one-line CLI edit.
(c) If the current behavior (CLI reads `pages_filtered_in` from
    `pipeline_runner.PipelineStats`) is already correct, ARCH-10 should be
    closed as not-a-defect and the docs/cli.md "Bug" note removed.

The implementer will not guess among these; the code as written is internally
consistent and working, so there is no in-path one-line fix that satisfies the
ticket's acceptance criteria without regressing the live CLI path.
