# TICKET-330 — content_validation.ContentValidator class docstring over-promises "configurable custom rules"

- Status: OPEN
- Class: (b) doc/behavior drift
- Module: personal_index/content_validation.py
- Issue: #498

## Symptom
The `ContentValidator` class docstring (lines 88-92) claims the validator
"Checks for required fields, valid URLs, proper date formats, and
configurable custom rules." There is no custom-rule mechanism anywhere in
the module: no add_rule/register/callback/predicate API, and `__init__`
accepts only `required_fields`, `max_title_length`, and `max_url_length`.
`validate()`/`_validate_item()` run a fixed set of built-in checks
(`_check_required_fields`, `_validate_url`, `_validate_title`,
`_validate_score`, `_validate_dates`). The "configurable custom rules"
capability is an over-promise.

## Evidence
- `sed -n '88,92p' personal_index/content_validation.py` shows the class
  docstring ending with "and configurable custom rules."
- `grep -n 'custom\|register\|callback\|predicate\|add_rule\|rule'
  personal_index/content_validation.py` matches only line 3 (module
  docstring "validation rules and validators"), line 88 ("against defined
  rules"), and line 91 ("configurable custom rules"). No custom-rule API
  exists.
- `__init__` (lines 94-102) signature:
  `def __init__(self, required_fields=None, max_title_length=500,
  max_url_length=2048)`.
- `_validate_item` (lines 120-130) runs only the five fixed built-in checks.

## Minimal additive fix
Correct the class docstring to describe only the capabilities actually
implemented. Change line 91 from
"and configurable custom rules." to
"and configurable field requirements and length limits." (the two real
configurabilities: `required_fields` and the max-length thresholds).

Add ONE regression test
`TestContentValidatorDocstring::test_docstring_does_not_promise_custom_rules`
that asserts "custom rules" is absent from `ContentValidator.__doc__`, so the
over-promise cannot silently return.
