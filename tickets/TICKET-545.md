# TICKET-545: exact-contract docstrings for content_validator.rules has_min_length / has_valid_url / has_valid_score + pinning test

Status: OPEN
Issue: #965
Module: personal_index/content_validator/rules.py
Type: type-a (public functions lacking exact-contract docstring + pinning test)

## Symptom
The three rule factory functions in content_validator/rules.py have terse one-line
docstrings that omit the exact contract the code actually delivers:

- has_min_length(field, min_length): docstring says only "checks minimum string
  length" / "Returns: Callable that returns True if field meets length." It omits:
  (1) a MISSING field (item.get(field) is None) returns False, (2) the value is
  coerced via str(value) so NON-STRING values (e.g. int 12345) are measured by the
  length of their string form, (3) the comparison is INCLUSIVE (>= min_length).

- has_valid_url(field): docstring says only "checks URL validity" / "Returns:
  Callable that returns True if URL is valid." It omits: (1) "valid" means the
  string STARTS WITH "http://" or "https://" ONLY (ftp://, file://, etc. fail),
  (2) an empty string fails, (3) a missing field fails.

- has_valid_score(): docstring says only "checks score is in valid range" /
  "Returns: Callable that returns True if score is between 0 and 1." It omits:
  (1) a MISSING score (None) returns True (treated as valid), (2) the range is
  INCLUSIVE [0.0, 1.0] (both 0 and 1 pass), (3) only int/float types pass -- a
  string like "0.5" fails, (4) bool is a subclass of int so True/False pass.

## Evidence (verified live)
has_valid_score(): {} -> True; {'score':0.5} -> True; {'score':1.5} -> False;
{'score':0} -> True; {'score':1} -> True; {'score':True} -> True;
{'score':False} -> True; {'score':'0.5'} -> False.
has_valid_url('url'): {'url':'https://x.com'} -> True; {'url':'http://x.com'} ->
True; {'url':'ftp://x.com'} -> False; {'url':''} -> False; {} -> False.
has_min_length('title',3): {'title':'Hello'} -> True; {'title':'Hi'} -> False;
{} -> False; {'title':12345} -> True; {'title':None} -> False.

## Existing coverage (tests/test_content_validator.py)
TestValidationRule pins: has_min_length happy/short/missing; has_valid_url
https/ftp/missing; has_valid_score 0.5/1.5/missing. It does NOT pin: the str()
coercion of non-string values, the inclusive bounds (0 and 1), the bool-as-int
pass, the string-score fail, the http:// (non-https) pass, the empty-string fail,
or the docstring contract phrases.

## Minimal additive fix
Reword the three docstrings to state the exact contract (missing-field behavior,
str() coercion, inclusive bounds, bool-as-int, http/https-only prefix, empty/
missing fail). Add a pinning test class TestRulesDocstring545 asserting the key
contract phrases appear in the docstrings AND re-pinning the non-obvious behaviors
(str() coercion, inclusive 0/1 bounds, bool pass, string-score fail, http:// pass,
empty-string fail).

## Notes
- No reword commit exists in git history for rules.py (git log shows only the
  original "feat: add content_validator module" commit) -- a fresh type-a case,
  not a doc-drift recovery.
- Ticket number 545: 544 is already claimed by PR #964 (content_scoring.
  _score_freshness, open); 543 is the highest RESOLVED on origin/main.
