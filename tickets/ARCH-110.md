# ARCH-110 — validator.py is a dead near-twin of content_validation.py: two incompatible `ValidationResult` and two incompatible `ContentValidator` types for the same domain, and an orphaned `URLValidator` with no live home

- **Status:** OPEN
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** personal_index/validator.py (DEAD module — 0 production importers; see docs/validator.md) + personal_index/content_validation.py (the live content-validation twin it was meant to mirror)
- **Issue:** #1529 (ARCH-110, left OPEN as the implementer claim queue — no `Closes` in PR body)

## Symptom

`validator.py` is a dead parallel implementation of the content-validation
system: it is never imported anywhere in `personal_index/` (witness below), and
it defines **two types that collide with the live `content_validation.py`
twin** for the same domain — a `ValidationResult` and a `ContentValidator` —
whose contracts have silently diverged. It also defines a `URLValidator` that
exists **only** in this dead module (no live standalone URL validator).

The concrete, verifiable holes are three:

1. **Two incompatible `ValidationResult` types.** This module's
   `ValidationResult` (validator.py:14) is a dataclass with `valid: bool` and
   plain `str` `errors`/`warnings` lists. The live
   `content_validation.ValidationResult` (content_validation.py:33) is a
   dataclass with `is_valid: bool` and `ValidationError`-object
   `errors`/`warnings` lists plus `items_valid`/`items_invalid` tallies. Same
   name, same domain, but a different validity field name (`valid` vs
   `is_valid`) and a different element type (`str` vs `ValidationError`) — a
   consumer cannot pass one where the other is expected.

2. **Two incompatible `ContentValidator` types.** This module's
   `ContentValidator` (validator.py:124) validates a single `str` (length /
   word-count / link-ratio / whitespace). The live
   `content_validation.ContentValidator` (content_validation.py:100) validates
   `list[dict]` items (required fields / title / url / score / dates). Same
   name, same domain, completely different input type and checks.

3. **`URLValidator` is orphaned.** `URLValidator` (validator.py:39) — the
   scheme allow-list / blocked-domain / blocked-path surface — exists **only**
   in this dead module. The live `content_validation` validates URLs only as a
   sub-check of dict items; there is no live standalone URL validator, so this
   surface has no live home.

This is the dead-module + divergent-contract class (ARCH-100/102/105/106/107/108
pattern): the module ships a public validation API whose contract (a
`ValidationResult`/`ContentValidator` interchangeable with the live twin) it
does not fulfill, and which is incompatible with the live twin it was meant to
mirror.

## Evidence (file:line)

DEAD-MODULE witness:
- `grep -rn 'from personal_index.validator import\|from .validator import\|import validator\b\|from personal_index import validator'
  personal_index/ --include=*.py` returns **nothing** (rc=1) — validator.py is
  never wired.
- Its only consumers are tests: `tests/test_validator.py`
  (`from personal_index.validator import ContentValidator, URLValidator,
  ValidationResult`) and `tests/deep/test_validator_url_adversarial.py`
  (`from personal_index.validator import ...`).

Dead-module `ValidationResult` (validator.py:14-37):
- validator.py:14 — `@dataclass class ValidationResult:`.
- validator.py:17 — `valid: bool` (the validity field is named `valid`, not
  `is_valid`).
- validator.py:18-19 — `errors: list[str]` / `warnings: list[str]` (plain
  `str` elements, not `ValidationError` objects).
- validator.py:21 / validator.py:30 — `add_error` / `add_warning` take a
  single `message: str`.

Dead-module `ContentValidator` (validator.py:124-178):
- validator.py:124 — `class ContentValidator:`.
- validator.py:141 — `def validate(self, content: str) -> ValidationResult:`
  (input is a single `str`).
- validator.py:127-129 — `MIN_CONTENT_LENGTH = 50`,
  `MAX_CONTENT_LENGTH = 10_000_000`, `MIN_WORD_COUNT = 10`.

Dead-module `URLValidator` (validator.py:39-122) — orphaned:
- validator.py:39 — `class URLValidator:`.
- validator.py:42-44 — `SCHEMES = {"http","https","ftp","ftps"}`,
  `MAX_URL_LENGTH = 2048`, `MAX_DOMAIN_LENGTH = 253`.
- validator.py:58 — `def validate(self, url: str) -> ValidationResult:`.
- validator.py:119 — `def validate_batch(self, urls: list[str]) ->
  list[tuple[str, ValidationResult]]:`.
- No `URLValidator` (or standalone URL validator) exists in
  `content_validation.py` — the live module validates URLs only inside
  `ContentValidator.validate(items: list[dict])` (content_validation.py:120).

Live-twin divergent types — the contract the dead module collides with:
- personal_index/content_validation.py:33 — `class ValidationResult:`.
- personal_index/content_validation.py:44 — `is_valid: bool = True` (field
  named `is_valid`, not `valid`).
- personal_index/content_validation.py:45-46 — `errors: list[ValidationError]`
  / `warnings: list[ValidationError]` (`ValidationError` objects, not `str`).
- personal_index/content_validation.py:47-48 — `items_valid: int = 0` /
  `items_invalid: int = 0` (tallies the dead module lacks).
- personal_index/content_validation.py:50 — `def add_error(self, field,
  message, value=None)` (three args, not one).
- personal_index/content_validation.py:100 — `class ContentValidator:`.
- personal_index/content_validation.py:117 — `def validate(self, items:
  list[dict[str, Any]]) -> ValidationResult:` (input is `list[dict]`, not
  `str`).

## Proposed fix (implementer)

Two acceptable resolutions; pick one and record it in the ticket:

(a) **Retire the dead twin** (preferred — the module has 0 production
    importers and its `ValidationResult`/`ContentValidator` collide with the
    live ones): delete `personal_index/validator.py` and its test files
    (`tests/test_validator.py`, `tests/deep/test_validator_url_adversarial.py`
    — the latter is the validator's path, so coordinate with the validator),
    and remove the docs/validator.md page. If the `URLValidator` surface is
    wanted, promote it into the live `content_validation` module as a
    standalone URL validator (with the live `ValidationResult` contract) rather
    than keeping the dead twin.

(b) **Explicitly defer / document the divergence** (if the module stays dead):
    keep the module, but state in the `ValidationResult` and `ContentValidator`
    docstrings and in docs/validator.md that this module is **dead** (0
    importers) and that its `ValidationResult` (`valid` / `str` elements) and
    `ContentValidator` (single-`str` input) are **intentionally NOT** the live
    `content_validation` types (`is_valid` / `ValidationError` elements /
    `list[dict]` input) — so a future reader does not assume the two are
    interchangeable.

Either way, the docs/validator.md "Contract hole (ARCH-110)" entry must reflect
the chosen resolution.

## Acceptance criteria

- [ ] The dead-module status (0 production importers) is stated in
      docs/validator.md header (done in this PR) and in this ticket.
- [ ] The near-name distinction from `content_validation.py` (and the older
      `content_validator` index line) is stated in the page header (done in
      this PR).
- [ ] The dual-`ValidationResult` + dual-`ContentValidator` + orphaned-
      `URLValidator` divergences are pinned with file:line evidence (above).
- [ ] A resolution (a) or (b) is chosen and the docs page updated to match.
- [ ] Pinning test (implementer, tests/** — NOT the architect's path): one
      behavior test that pins the chosen resolution — for (a) assert the dead
      module is gone (import fails) or that the promoted `URLValidator` returns
      the live `content_validation.ValidationResult` (assert `is_valid` exists
      and `errors` elements are `ValidationError`); for (b) assert the dead
      `ValidationResult` has a `valid` field (not `is_valid`) and `str` error
      elements, and that the dead `ContentValidator.validate` accepts a `str`
      (pinning the documented divergence from the live `list[dict]` contract).
      NOTE: the existing `tests/test_validator.py` and
      `tests/deep/test_validator_url_adversarial.py` already pin the CURRENT
      dead-module behavior and are the witness that the corrected docstring
      matches reality — no new test is required for a doc-only (b) resolution.

## Self-review checklist (architect)

- [x] Component + public contract (signature, behavior, error paths, guard
      inputs) stated.
- [x] Acceptance criteria present.
- [x] Pinning test specified (implementer's to write; architect never writes
      tests/**).
- [x] Matching docs/validator.md update shipped in the SAME PR.
- [x] DEAD-MODULE witness (0 importers) recorded.
- [x] Near-name-collision disambiguation (validator vs content_validation vs
      content_validator) recorded.
- [x] No personal_index/** or tests/** written by the architect.
