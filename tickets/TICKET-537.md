# TICKET-537: QualityChecker.check docstring omits exact scoring contract

Status: RESOLVED (merged via PR #950, issue #949 closed)
Module: personal_index/content_validator/quality.py
Method: QualityChecker.check (def at line 42)

## Symptom
The `check` docstring is a terse two-line stub:
    "Check the quality of a content item."
    "Args: item: Content item to check."
    "Returns: QualityScore with assessment details."
It does NOT state the exact contract that the code actually delivers:
  - completeness = (count of required_fields present and truthy) /
    len(required_fields); 0.0 when required_fields is empty;
  - richness = (count of rich_fields present and truthy) /
    len(rich_fields); 0.0 when rich_fields is empty;
  - overall = round(completeness * 0.6 + richness * 0.4, 4) -- a fixed
    60/40 weighting, rounded to 4 decimal places;
  - issues is built in a fixed order: one "Missing required field: <f>"
    entry per absent/falsy required field (in required_fields order), then
    "Title is too short" when title is present and len(str(title)) < 3,
    then "Content is too short" when content is present and
    len(str(content)) < 10;
  - completeness and richness are each rounded to 4 decimal places in the
    returned QualityScore (overall is rounded to 4 as well).
A reader of the docstring cannot tell the 0.6/0.4 weighting, the exact
issue message strings, the <3 / <10 length thresholds, or the rounding.
Sibling methods check_batch / filter_by_quality are also terse but their
contracts are trivial (map check over items; keep items whose
check(item).overall >= min_score); check is the one with a rich, non-obvious
contract that is currently undocumented.

## Evidence (verified by running the code)
  check({'id':'1'}).overall            -> 0.2   (comp 0.3333, rich 0.0)
  check({'id':'1','title':'A good title','content':'This is a long enough content string.'})
    -> overall 0.6, comp 1.0, rich 0.0, issues []
  check({'id':'1','title':'A good title','content':'This is a long enough content string.','tags':['x']})
    -> overall 0.7, comp 1.0, rich 0.25
  check({'id':'1','title':'ab','content':'short'})
    -> overall 0.6, comp 1.0, rich 0.0
    issues ['Title is too short', 'Content is too short']
  check({}).overall                    -> 0.0, comp 0.0, rich 0.0
    issues ['Missing required field: id', 'Missing required field: title',
            'Missing required field: content']
  check(perfect item).overall          -> 1.0, comp 1.0, rich 1.0, issues []

Existing behavioral tests (tests/test_content_validator.py TestQualityChecker:
test_perfect_quality, test_poor_quality, test_filter_by_quality,
test_batch_check) pin only the endpoints (perfect -> 1.0, empty -> 0.0) and
do NOT pin the 0.6/0.4 weighting, the exact issue message strings, the
<3 / <10 thresholds, or the 4-place rounding. The behavior is correct; only
the docstring contract is missing. No reword commit exists in history for
quality.py -- a fresh "add exact-contract docstring + pinning test" case
(type a), not a doc-drift recovery.

## Minimal additive fix
Reword the check docstring to state the exact contract (completeness /
richness ratios, the 0.6/0.4 weighted overall rounded to 4 places, the fixed
issue-message strings and their order, the <3 / <10 length thresholds, and
the 4-place rounding of completeness/richness). Add a pinning test class
TestCheckDocstring537 mirroring the TestComputeDocstring535 pattern,
asserting the docstring states the contract (key phrases: "0.6", "0.4",
"Missing required field", "Title is too short", "Content is too short",
"round") plus behavioral pins for the weighted formula, the exact issue
message strings/order, and the length thresholds.

## Issue
Issue: #949
