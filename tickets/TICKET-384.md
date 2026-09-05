# TICKET-384: validator.py placeholder docstrings (class-(b) doc-drift)

Status: OPEN

## File
personal_index/validator.py

## Symptom
Five methods carry placeholder "Process <name>." docstrings that do not
describe the behavior the body actually performs:
- ValidationResult.add_error (line 22)
- ValidationResult.add_warning (line 31)
- URLValidator.validate (line 59)
- ContentValidator.validate (line 141)

## Evidence
- L22: `"""Process add_error.` — body sets `self.valid = False` and appends to `self.errors`.
- L31: `"""Process add_warning.` — body appends to `self.warnings` and does NOT touch `self.valid`.
- L59: `"""Process validate."""` — body runs length/scheme/domain/path/fragment checks and returns a ValidationResult valid iff no errors.
- L141: `"""Process validate.` — body checks length/word-count/link-ratio/whitespace and returns a ValidationResult.

## Minimal additive fix
Reword each docstring to state the exact behavior the body performs, and add
ONE behavior test pinning the corrected add_warning claim (appends to
warnings, leaves valid unchanged) against the returned object.

## Issue
Issue: #606
