# TICKET-548: SchemaValidator.validate / is_valid / validate_batch exact-contract docstrings + pinning test

Status: OPEN
Module: personal_index/content_validator/schema.py
Methods: SchemaValidator.validate, SchemaValidator.is_valid, SchemaValidator.validate_batch
Type: (a) public methods lacking an exact-contract docstring + pinning test

## Symptom
The three docstrings are terse stubs that omit the exact contract the code
actually delivers.

validate (line ~50) says only "Validate an item against the schema and rules."
/ "List of RuleResult objects." and omits:
  (1) the result list is built in a fixed three-stage order:
      stage 1 always appends ONE "required_fields" RuleResult (severity
      "error") whose passed flag is True iff every name in
      schema.required_fields is present in item;
  (2) stage 2 iterates schema.field_types in insertion order and, for each
      (field_name, expected_type), appends a FAILING RuleResult with
      rule_name "field_type_<field_name>" (severity "error") ONLY when
      item.get(field_name) is not None AND not isinstance(value, expected_type);
      a None value is TOLERATED (no result appended) - this None-tolerance is
      the subtle contract point the stub hides;
  (3) stage 3 appends rule.validate(item) for each rule in self.rules, in
      self.rules order.

is_valid (line ~88) says only "Check if an item passes all validations." /
"True if all validations pass." and omits that it is exactly
all(r.passed for r in self.validate(item)) - i.e. True iff EVERY RuleResult
from validate() has passed=True. (validate always appends at least the
required_fields result, so the list is never empty.)

validate_batch (line ~99) says only "Validate multiple items." / "Dict mapping
item ID to validation results." and omits that the key is
str(item.get("id", "unknown")) (id is stringified; a missing id maps to
"unknown") and that duplicate ids overwrite (last item wins).

## Evidence
- validate body (lines ~57-86): three sequential blocks; the field_types loop
  guards `if value is not None and not isinstance(value, expected_type)`.
- is_valid body (lines ~96-97): `results = self.validate(item)` then
  `return all(r.passed for r in results)`.
- validate_batch body (lines ~108-112): `item_id = str(item.get("id", "unknown"))`
  then `results[item_id] = self.validate(item)`.
- No docstring pinning test exists for these three methods (tests/
  test_content_validator.py has only functional tests: test_valid_item,
  test_field_types, test_batch_validate).

## Minimal additive fix
Reword the three docstrings to state the exact contract above (three-stage
order, None-tolerance for typed fields, all-passed semantics, stringified-id
keying with "unknown" fallback and last-wins overwrite), and add ONE pinning
test class that (a) asserts the docstrings state the key contract fragments
and (b) pins the behavior: the None-tolerance path (a typed field present as
None appends no field_type result), the three-stage result order, is_valid
True-when-all-pass, and validate_batch "unknown" keying + last-wins
overwrite.

## Issue
Issue: #974
