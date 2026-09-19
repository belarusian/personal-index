# ARCH-102 — dedup CLI prints the similarity threshold as Score:, not the measured similarity

- **Status:** CLOSED (architect close, cycle 319; was VERIFIED (validator cycle 271 @ main 76e12b6; Option A confirmed: DuplicateGroup.similarity_score field docstring at content_dedup.py:19-21 states threshold-not-measured, CLI relabeled Score:->Threshold: at cli_dedup.py:118; pinning test test_score_is_threshold + 67 others in tests/deep/test_cli_dedup_adversarial.py 68 passed; [was IMPLEMENTED 2026-09-16 impl330 cycle 330 Option A PR #1575]))
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** personal_index/cli_dedup.py (the LIVE dedup command) + personal_index/content_dedup.py (the ContentDeduplicator.dedup_by_similarity engine it drives)
- **Issue:** #1502

## Symptom

When a user runs personal-index dedup --method similarity (or the default
--method all, which includes the similarity pass) and duplicate groups are
found, the report prints one line per group:

    Representative: <url>
    Method: similarity
    Score: 0.90
      Duplicate: <url>

The Score: value is always the configured --similarity-threshold (default
0.90), not the actual word-overlap similarity between the representative and
its duplicates. Every similarity group shows the same number — the threshold —
so the field conveys no information about how similar the group members
actually are.

## Evidence (file:line)

- personal_index/content_dedup.py:388 — dedup_by_similarity builds each group
  with similarity_score=self.similarity_threshold (the threshold), not a
  measured value.
- personal_index/content_dedup.py:417 — _find_similarity_group computes
  text_similarity(text_a, text_b) (the real Jaccard overlap) to decide whether
  item j joins the group, but discards the computed value; only the boolean
  >= self.similarity_threshold comparison is used.
- personal_index/content_dedup.py:143-168 — text_similarity returns the real
  Jaccard similarity len(intersection)/len(union) (a value in [0.0, 1.0]), so
  a measured score is available but unused.
- personal_index/cli_dedup.py:118 — _display_duplicate_groups prints
  click.echo(f"  Score: {group.similarity_score:.2f}"), surfacing the
  threshold as if it were the measured score.
- personal_index/content_dedup.py:20 — the DuplicateGroup.similarity_score
  field has no docstring stating what it means for the similarity method, so
  the threshold-as-score behavior is undocumented at the field level (the
  dedup_by_similarity docstring at line 360-362 does state it, but the field
  and the CLI output do not).

## Classification

This is a class-(b) docstring/contract over-promise surfaced through the CLI,
with a genuine untested-invariant hole:

- The dedup_by_similarity docstring is accurate (it says
  similarity_score = self.similarity_threshold).
- But the field DuplicateGroup.similarity_score (line 20) is undocumented, and
  the CLI labels the value Score: — a name that implies a measured per-group
  similarity. The user-facing contract (the report) therefore over-promises:
  it presents the threshold as a score.
- The deep test test_score_is_threshold
  (tests/deep/test_cli_dedup_adversarial.py:360-367) pins the current
  threshold-as-score behavior (similarity_threshold=0.5 ->
  similarity_score == 0.5). That test is the WITNESS that the corrected
  docstring/label matches reality for the doc-only resolution below.

## Proposed fix (two acceptable resolutions — implementer picks ONE)

Option A (doc-only, minimal, recommended): make the field and the CLI label
honest about what the value is.

1. Add a docstring to DuplicateGroup.similarity_score (content_dedup.py:20)
   stating: for exact_hash/normalized_url groups the score is 1.0; for
   similarity groups the score is the configured similarity_threshold (the
   grouping cutoff), not the measured per-pair Jaccard overlap.
2. Relabel the CLI line in _display_duplicate_groups (cli_dedup.py:118) from
   Score: to something that does not imply a measured value, e.g. Threshold:
   (or Min similarity:), so the printed number is not misread as a per-group
   similarity.

   This is doc/label-only: no behavior change, so the existing deep test
   test_score_is_threshold remains the witness (it still passes unchanged).

Option B (behavioral, larger): make similarity_score carry the real measured
value.

1. Change _find_similarity_group (content_dedup.py:401-421) to also return the
   measured text_similarity for each grouped pair (or the minimum across the
   group), and thread it into the DuplicateGroup construction at
   content_dedup.py:388.
2. Update the dedup_by_similarity docstring (line 360-362) to state the score
   is the measured value.
3. Update the deep test test_score_is_threshold
   (tests/deep/test_cli_dedup_adversarial.py:360-367) — it currently pins the
   threshold behavior and would FAIL under Option B. (This is the VALIDATOR's
   path; if Option B is chosen the ticket must be re-scoped so the deep-test
   reconciliation is owned by the validator.)

Option A is the minimal, doc-only fix and keeps the existing deep test as the
witness. Option B changes behavior and requires a deep-test change (validator
path) — prefer A unless a product decision demands the measured value.

## Acceptance criteria

- [ ] DuplicateGroup.similarity_score has a docstring stating its meaning per
      dedup_method (1.0 for exact/normalized; the configured threshold for
      similarity).
- [ ] The dedup CLI no longer labels the threshold value as a measured Score:
      (Option A: relabeled; Option B: prints the measured value).
- [ ] docs/cli_dedup.md Known contract hole section is updated to reflect the
      resolution (moved to a resolved note or removed).
- [ ] (Option A) The existing deep test test_score_is_threshold still passes
      unchanged (it is the witness). (Option B) the deep test is reconciled by
      the validator and the ticket re-scoped accordingly.
- [ ] docs/README.md index entry for cli_dedup.md is present (shipped in the
      same PR as this ticket).

## Pinning tests to add (implementer)

- Option A (doc/label-only): no new behavior test is required — the existing
  test_score_is_threshold (tests/deep/test_cli_dedup_adversarial.py:360-367)
  is the witness that the corrected field docstring + relabeled CLI match the
  actual threshold-as-score behavior. If a label change is made, add ONE
  CLI-level test asserting the printed line uses the new label (e.g.
  Threshold:) for a similarity group, pinning the user-facing contract.
- Option B (behavioral): add ONE behavior test that pins the CORRECTED claim
  against the returned object — a dedup_by_similarity call on two items with a
  known Jaccard overlap (e.g. threshold 0.5, two identical contents ->
  measured 1.0, or a partial overlap -> the exact len(intersection)/len(union)
  value) asserting group.similarity_score == <measured value> (NOT the
  threshold), alongside the guard-path input (empty/missing content -> items
  never group, per the existing test_empty_content_never_groups). This
  requires the validator to reconcile test_score_is_threshold.

## Self-review checklist (architect)

- [x] CONFIRM-WIRED-BEFORE-AUDIT: grep -rn 'cli_dedup' personal_index/
      --include=*.py -> cli.py:26 import; grep -n 'dedup' cli.py ->
      cli.py:1509 main.add_command(dedup). The dedup command is LIVE
      (imported + registered), not a dead parallel implementation.
- [x] NEAR-NAME-COLLISION DISAMBIGUATION: the page header states this page
      documents cli_dedup.py (the dedup command) and is distinct from the
      underlying engine content_dedup.py (docs/dedup.md).
- [x] WITNESS-ROLE: the deep test test_score_is_threshold
      (tests/deep/test_cli_dedup_adversarial.py:360-367) already pins the
      CURRENT threshold-as-score behavior, so the minimal fix is doc/label-only
      (Option A) and that test is the witness (no new test, no code change).
- [x] Evidence is file:line, verified against current code.
- [x] docs/cli_dedup.md spec page + docs/README.md index entry shipped in the
      SAME PR as this ticket.
- [x] No personal_index/** or tests/** written by the architect (this ticket
      is design-only; the fix is the implementer's).
