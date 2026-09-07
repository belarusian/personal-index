# Validation (`personal_index.content_validator`)

Status: **spec** — audited against current code (cycle 169).

A package (`content_validator/`) with three sub-modules: `rules.py`
(rule primitives), `quality.py` (quality scoring), `schema.py` (schema
validation). `__init__.py` re-exports `ContentSchema`, `QualityChecker`,
`RuleResult`, `SchemaValidator`, `ValidationRule`.

## rules.py

- `RuleResult` (dataclass): `rule_name`, `passed`, `message` (default `""`),
  `severity` (default `"info"`).
- `ValidationRule` (dataclass): `name`, `check`
  (`Callable[[dict[str, Any]], bool]`), `message` (default `""`), `severity`
  (default `"warning"`).
  - `validate(item) -> RuleResult` — `passed = self.check(item)`; returns
    `RuleResult(rule_name=self.name, passed=passed,
    message=self.message if not passed else "", severity=self.severity)`.
    **Guard path:** on pass the `message` is `""` (the rule's message is only
    surfaced on failure).
- `has_required_fields(fields) -> Callable` — returns a callable that is True
  iff `all(f in item for f in fields)` (presence only; falsy values still
  count as present).
- `has_min_length(field, min_length) -> Callable` — True when the field is
  present and `len(str(value)) >= min_length`; a missing field
  (`item.get(field) is None`) returns False. Non-string values are measured by
  the length of their `str(...)` form. Inclusive comparison.
- `has_valid_url(field) -> Callable` — True only when the field's string form
  starts with `http://` or `https://`; an empty or missing field fails.
- `has_valid_score() -> Callable` — True when `score` is absent (treated as
  valid) or is an `int`/`float` in the inclusive range `[0.0, 1.0]`. A string
  such as `"0.5"` fails; `bool` (an `int` subclass) passes.

## quality.py

- `QualityScore` (dataclass): `overall` (0.0), `completeness` (0.0),
  `richness` (0.0), `issues` (list, default `[]`).
- `QualityChecker` (dataclass): `required_fields` (default
  `["id", "title", "content"]`), `rich_fields` (default
  `["tags", "author", "summary", "score"]`).
  - `check(item) -> QualityScore` — `completeness` = (count of
    `required_fields` present **and truthy**) / `len(required_fields)`, `0.0`
    when `required_fields` is empty; `richness` = (count of `rich_fields`
    present and truthy) / `len(rich_fields)`, `0.0` when `rich_fields` is
    empty; `overall` = `round(completeness * 0.6 + richness * 0.4, 4)` (fixed
    60/40 weighting); `issues` built in a fixed order — one
    `"Missing required field: <f>"` per absent/falsy required field (in
    `required_fields` order), then `"Title is too short"` when `title` is
    present and `len(str(title)) < 3`, then `"Content is too short"` when
    `content` is present and `len(str(content)) < 10`. `completeness`,
    `richness` and `overall` are each rounded to 4 places.
  - `check_batch(items) -> list[tuple[dict, QualityScore]]` — one
    `(item, check(item))` tuple per item, in input order.
  - `filter_by_quality(items, min_score=0.5) -> list[dict]` — the items whose
    `check(item).overall >= min_score`, in input order.

## schema.py

- `ContentSchema` (dataclass): `name` (default `"default"`),
  `required_fields` (default `["id", "title"]`), `optional_fields` (default
  `[]`), `field_types` (default `{}`).
- `SchemaValidator` (dataclass): `schema` (default `ContentSchema()`),
  `rules` (default `[]`).
  - `validate(item) -> list[RuleResult]` — a fixed three-stage order:
    (1) one `"required_fields"` result (severity `"error"`, passed iff every
    `schema.required_fields` name is present); (2) for each
    `(field_name, expected_type)` in `schema.field_types` (insertion order), a
    FAILING `"field_type_<field_name>"` result (severity `"error"`) appended
    ONLY when `item.get(field_name) is not None` and
    `not isinstance(value, expected_type)` (a present-`None` value is
    tolerated); (3) `rule.validate(item)` for each rule in `self.rules`, in
    order.
  - `is_valid(item) -> bool` — `all(r.passed for r in validate(item))` (the
    list is never empty: `validate` always appends the `required_fields`
    result).
  - `validate_batch(items) -> dict[str, list[RuleResult]]` — maps each item to
    its `validate` results; the key is `str(item.get("id", "unknown"))`
    (missing id maps to `"unknown"`; duplicate ids overwrite, last wins).

## Contract holes
- **`ValidationRule.validate` docstring drift (-> ARCH-5).** The docstring is a
  blanket "Returns: RuleResult with validation outcome." that does not state
  the guard path (message is `""` on pass) or that `severity` is
  `self.severity`. The three built-in rule factories (`has_min_length`,
  `has_valid_url`, `has_valid_score`) and `SchemaValidator.validate` /
  `is_valid` / `validate_batch` were already reworded to exact-contract form in
  prior cycles (165/TICKET-545, 169/TICKET-548).
- **`QualityChecker.check_batch` / `filter_by_quality` docstrings are blanket**
  ("Check quality of multiple items." / "Filter items by minimum quality
  score.") — accurate but do not enumerate the returned shape / the
  `overall >= min_score` predicate. Lower priority than the rules/schema
  drifts; deferred (no separate ticket this cycle).
