Status: CLAIMED 2026-09-07
Kind: ARCH
Author: architect (cycle 169)
Issue: #986

# ARCH-5: `ValidationRule.validate` blanket docstring

## Component
`personal_index.content_validator.rules.ValidationRule.validate`
(content_validator/rules.py).

## Symptom
The docstring is a blanket "Returns: RuleResult with validation outcome." that
does not state the guard path (the `message` is `""` on pass) or that
`severity` is `self.severity`. The three built-in rule factories
(`has_min_length`, `has_valid_url`, `has_valid_score`) and
`SchemaValidator.validate` / `is_valid` / `validate_batch` were already
reworded to exact-contract form in prior cycles (165/TICKET-545,
169/TICKET-548); `ValidationRule.validate` was missed.

## Public contract (the code is the truth)
`validate(item: dict[str, Any]) -> RuleResult`:
- **Behavior:** `passed = self.check(item)`; returns
  `RuleResult(rule_name=self.name, passed=passed,
  message=self.message if not passed else "", severity=self.severity)`.
- **Guard path:** on PASS the `message` is `""` (the rule's configured message
  is surfaced ONLY on failure); `severity` is always `self.severity` (the
  rule's configured severity, default `"warning"`), regardless of pass/fail.
- **Return fields:** `rule_name` = `self.name`; `passed` = the check's bool;
  `message` = `self.message` on fail, `""` on pass; `severity` = `self.severity`.
- **Side effects:** none (pure).

## Acceptance criteria
- The docstring states the guard path (message `""` on pass) and that
  `severity` is `self.severity`, per parts 1-3 of docs/CONTRACTS.md.
- ONE pinning test asserts the RETURNED `RuleResult` for BOTH the pass case
  (a `check` that returns True -> `passed=True`, `message=""`) AND the fail
  case (a `check` that returns False -> `passed=False`, `message=self.message`)
  — the guard path (pass) alongside the normal path (fail).

## Pinning tests to add
`test_validation_rule_validate_pinned` (pass + fail input), asserting the
returned `RuleResult` fields.

## Docs page it updates
`docs/validation.md` (the `ValidationRule.validate` entry + the contract-holes
line).
