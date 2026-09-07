"""Adversarial deep tests for personal_index.content_validator.

Cycle 136 - VALIDATOR probe.

Targets (never-probed subsystem, exact-contract docstrings):
  - ValidationRule.validate: guard path (message "" on pass), severity
    always self.severity, exact return fields, purity (no side effects).
  - has_required_fields: empty list, missing/present fields.
  - has_min_length: missing field, str-coercion, inclusive boundary,
    out-of-range min_length, unicode length.
  - has_valid_url: http/https only, empty, missing, other schemes,
    non-string coercion.
  - has_valid_score: missing, inclusive [0,1], int/float only, bool
    subclass edge, out-of-range.
  - SchemaValidator.validate: three-stage order, None-tolerated field
    types, field_type failure naming.
  - SchemaValidator.is_valid: all-pass property.
  - SchemaValidator.validate_batch: id stringification, missing id ->
    "unknown", duplicate id overwrite (last wins).
  - End-to-end CLI run (installed entry point).
"""

from __future__ import annotations

from typing import Any


from personal_index.content_validator.rules import (
    RuleResult,
    ValidationRule,
    has_min_length,
    has_required_fields,
    has_valid_score,
    has_valid_url,
)
from personal_index.content_validator.schema import (
    ContentSchema,
    SchemaValidator,
)


# ---------------------------------------------------------------------------
# ValidationRule.validate
# ---------------------------------------------------------------------------

class TestValidationRuleValidate:
    def test_pass_guard_message_empty(self):
        # Guard path: check True -> message "" even though a message is set.
        rule = ValidationRule(
            name="r", check=lambda item: True,
            message="should not surface", severity="error",
        )
        res = rule.validate({"x": 1})
        assert res.rule_name == "r"
        assert res.passed is True
        assert res.message == ""
        assert res.severity == "error"

    def test_fail_surfaces_message(self):
        rule = ValidationRule(
            name="r", check=lambda item: False,
            message="boom", severity="warning",
        )
        res = rule.validate({})
        assert res.passed is False
        assert res.message == "boom"
        assert res.severity == "warning"

    def test_severity_always_self_severity(self):
        # severity is self.severity regardless of pass/fail.
        for check_val in (True, False):
            rule = ValidationRule(
                name="r", check=lambda item, cv=check_val: cv,
                message="m", severity="info",
            )
            assert rule.validate({}).severity == "info"

    def test_default_severity_is_warning(self):
        rule = ValidationRule(name="r", check=lambda item: True)
        assert rule.validate({}).severity == "warning"

    def test_pure_no_side_effects(self):
        # check must be called exactly once per validate; item not mutated.
        calls: list[Any] = []

        def check(item):
            calls.append(item)
            return True

        rule = ValidationRule(name="r", check=check)
        item = {"a": 1}
        rule.validate(item)
        rule.validate(item)
        assert len(calls) == 2
        assert item == {"a": 1}

    def test_result_is_rule_result(self):
        rule = ValidationRule(name="r", check=lambda item: True)
        assert isinstance(rule.validate({}), RuleResult)

    def test_unicode_message_roundtrip(self):
        rule = ValidationRule(
            name="r", check=lambda item: False,
            message="привет — ünïcode", severity="error",
        )
        assert rule.validate({}).message == "привет — ünïcode"


# ---------------------------------------------------------------------------
# has_required_fields
# ---------------------------------------------------------------------------

class TestHasRequiredFields:
    def test_empty_list_always_true(self):
        check = has_required_fields([])
        assert check({}) is True
        assert check({"a": 1}) is True

    def test_all_present(self):
        check = has_required_fields(["id", "title"])
        assert check({"id": "1", "title": "T"}) is True

    def test_missing_one(self):
        check = has_required_fields(["id", "title"])
        assert check({"id": "1"}) is False

    def test_present_but_none_value_counts_as_present(self):
        # contract: "all fields present" -> presence, not truthiness.
        check = has_required_fields(["id"])
        assert check({"id": None}) is True

    def test_duplicate_fields(self):
        check = has_required_fields(["id", "id"])
        assert check({"id": "1"}) is True
        assert check({}) is False


# ---------------------------------------------------------------------------
# has_min_length
# ---------------------------------------------------------------------------

class TestHasMinLength:
    def test_missing_field_false(self):
        check = has_min_length("title", 3)
        assert check({}) is False

    def test_none_value_false(self):
        check = has_min_length("title", 3)
        assert check({"title": None}) is False

    def test_inclusive_boundary(self):
        check = has_min_length("title", 3)
        assert check({"title": "ab"}) is False
        assert check({"title": "abc"}) is True
        assert check({"title": "abcd"}) is True

    def test_str_coercion_of_int(self):
        # 12345 -> "12345" length 5.
        check = has_min_length("n", 5)
        assert check({"n": 12345}) is True
        assert check({"n": 1234}) is False

    def test_str_coercion_of_float(self):
        check = has_min_length("n", 4)
        assert check({"n": 1.5}) is False   # "1.5" length 3
        assert check({"n": 12.5}) is True   # "12.5" length 4

    def test_zero_min_length(self):
        check = has_min_length("t", 0)
        assert check({"t": ""}) is True
        assert check({"t": "x"}) is True

    def test_negative_min_length(self):
        # len(str(v)) >= negative is always True when present.
        check = has_min_length("t", -1)
        assert check({"t": ""}) is True
        assert check({}) is False  # missing still False

    def test_unicode_length(self):
        check = has_min_length("t", 3)
        assert check({"t": "прив"}) is True  # 4 code points
        assert check({"t": "пр"}) is False   # 2 code points

    def test_empty_string_boundary(self):
        check = has_min_length("t", 1)
        assert check({"t": ""}) is False


# ---------------------------------------------------------------------------
# has_valid_url
# ---------------------------------------------------------------------------

class TestHasValidUrl:
    def test_http_ok(self):
        check = has_valid_url("url")
        assert check({"url": "http://example.com"}) is True

    def test_https_ok(self):
        check = has_valid_url("url")
        assert check({"url": "https://example.com"}) is True

    def test_other_schemes_fail(self):
        check = has_valid_url("url")
        for bad in ("ftp://x", "file:///x", "javascript:alert(1)", "httpx://x"):
            assert check({"url": bad}) is False, bad

    def test_empty_string_fails(self):
        check = has_valid_url("url")
        assert check({"url": ""}) is False

    def test_missing_field_fails(self):
        check = has_valid_url("url")
        assert check({}) is False

    def test_none_fails(self):
        check = has_valid_url("url")
        assert check({"url": None}) is False

    def test_non_string_coerced(self):
        # str(123) = "123" does not start with http(s)://.
        check = has_valid_url("url")
        assert check({"url": 123}) is False

    def test_prefix_only_no_slash(self):
        # "http://" prefix present but no host - still passes per contract
        # (startswith only).
        check = has_valid_url("url")
        assert check({"url": "http://"}) is True


# ---------------------------------------------------------------------------
# has_valid_score
# ---------------------------------------------------------------------------

class TestHasValidScore:
    def test_missing_score_true(self):
        check = has_valid_score()
        assert check({}) is True

    def test_none_score_true(self):
        check = has_valid_score()
        assert check({"score": None}) is True

    def test_inclusive_bounds(self):
        check = has_valid_score()
        assert check({"score": 0}) is True
        assert check({"score": 1}) is True
        assert check({"score": 0.0}) is True
        assert check({"score": 1.0}) is True
        assert check({"score": 0.5}) is True

    def test_out_of_range(self):
        check = has_valid_score()
        assert check({"score": -0.1}) is False
        assert check({"score": 1.1}) is False
        assert check({"score": 100}) is False

    def test_string_fails(self):
        check = has_valid_score()
        assert check({"score": "0.5"}) is False

    def test_bool_subclass_passes(self):
        # bool is subclass of int; True==1, False==0 both in [0,1].
        check = has_valid_score()
        assert check({"score": True}) is True
        assert check({"score": False}) is True

    def test_nan_fails(self):
        # NaN comparisons are False -> 0.0 <= nan <= 1.0 is False.
        check = has_valid_score()
        assert check({"score": float("nan")}) is False

    def test_inf_fails(self):
        check = has_valid_score()
        assert check({"score": float("inf")}) is False


# ---------------------------------------------------------------------------
# SchemaValidator.validate
# ---------------------------------------------------------------------------

class TestSchemaValidatorValidate:
    def test_three_stage_order(self):
        sv = SchemaValidator(
            schema=ContentSchema(
                name="s",
                required_fields=["id"],
                field_types={"n": int},
            ),
            rules=[
                ValidationRule(name="custom", check=lambda item: True),
            ],
        )
        # item: id present, n wrong type, custom passes.
        res = sv.validate({"id": "1", "n": "not-int"})
        assert [r.rule_name for r in res] == [
            "required_fields", "field_type_n", "custom",
        ]

    def test_required_fields_first_and_error(self):
        sv = SchemaValidator(schema=ContentSchema(required_fields=["id"]))
        res = sv.validate({})
        assert res[0].rule_name == "required_fields"
        assert res[0].passed is False
        assert res[0].severity == "error"

    def test_field_type_none_tolerated(self):
        # value present as None -> no field_type result appended.
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=[], field_types={"n": int}),
        )
        res = sv.validate({"n": None})
        assert all(r.rule_name != "field_type_n" for r in res)

    def test_field_type_missing_tolerated(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=[], field_types={"n": int}),
        )
        res = sv.validate({})
        assert all(r.rule_name != "field_type_n" for r in res)

    def test_field_type_failure_naming_and_severity(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=[], field_types={"n": int}),
        )
        res = sv.validate({"n": "x"})
        ft = [r for r in res if r.rule_name == "field_type_n"]
        assert len(ft) == 1
        assert ft[0].passed is False
        assert ft[0].severity == "error"
        assert "int" in ft[0].message

    def test_field_type_pass_appends_nothing(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=[], field_types={"n": int}),
        )
        res = sv.validate({"n": 5})
        assert all(r.rule_name != "field_type_n" for r in res)

    def test_custom_rules_in_order(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=[]),
            rules=[
                ValidationRule(name="a", check=lambda item: True),
                ValidationRule(name="b", check=lambda item: False,
                               message="b-fail"),
            ],
        )
        res = sv.validate({})
        names = [r.rule_name for r in res]
        assert names == ["required_fields", "a", "b"]
        assert res[2].message == "b-fail"

    def test_empty_schema_minimal(self):
        sv = SchemaValidator(schema=ContentSchema(required_fields=[]))
        res = sv.validate({})
        assert len(res) == 1
        assert res[0].rule_name == "required_fields"
        assert res[0].passed is True


# ---------------------------------------------------------------------------
# SchemaValidator.is_valid
# ---------------------------------------------------------------------------

class TestSchemaValidatorIsValid:
    def test_all_pass_true(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=["id"], field_types={"n": int}),
            rules=[ValidationRule(name="c", check=lambda item: True)],
        )
        assert sv.is_valid({"id": "1", "n": 5}) is True

    def test_any_fail_false(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=["id"], field_types={"n": int}),
        )
        assert sv.is_valid({"id": "1", "n": "x"}) is False

    def test_missing_required_false(self):
        sv = SchemaValidator(schema=ContentSchema(required_fields=["id"]))
        assert sv.is_valid({}) is False

    def test_property_matches_validate(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=["id"], field_types={"n": int}),
            rules=[ValidationRule(name="c", check=lambda item: False,
                                  message="no")],
        )
        for item in ({}, {"id": "1"}, {"id": "1", "n": 5},
                     {"id": "1", "n": "x"}, {"id": "1", "n": None}):
            expected = all(r.passed for r in sv.validate(item))
            assert sv.is_valid(item) is expected, item


# ---------------------------------------------------------------------------
# SchemaValidator.validate_batch
# ---------------------------------------------------------------------------

class TestSchemaValidatorValidateBatch:
    def test_missing_id_maps_unknown(self):
        sv = SchemaValidator(schema=ContentSchema(required_fields=[]))
        out = sv.validate_batch([{"a": 1}])
        assert list(out.keys()) == ["unknown"]

    def test_id_stringified(self):
        sv = SchemaValidator(schema=ContentSchema(required_fields=[]))
        out = sv.validate_batch([{"id": 123}])
        assert list(out.keys()) == ["123"]

    def test_duplicate_id_last_wins(self):
        sv = SchemaValidator(
            schema=ContentSchema(required_fields=["id"]),
            rules=[ValidationRule(name="c", check=lambda item: item.get("v") == 1)],
        )
        out = sv.validate_batch([
            {"id": "x", "v": 0},  # custom fails
            {"id": "x", "v": 1},  # custom passes -> last wins
        ])
        assert list(out.keys()) == ["x"]
        custom = [r for r in out["x"] if r.rule_name == "c"]
        assert custom[0].passed is True

    def test_empty_batch(self):
        sv = SchemaValidator(schema=ContentSchema(required_fields=[]))
        assert sv.validate_batch([]) == {}

    def test_none_id_stringified(self):
        # str(None) = "None" (not "unknown" - id key present).
        sv = SchemaValidator(schema=ContentSchema(required_fields=[]))
        out = sv.validate_batch([{"id": None}])
        assert list(out.keys()) == ["None"]


# ---------------------------------------------------------------------------
# End-to-end CLI run (installed entry point)
# ---------------------------------------------------------------------------

def test_end_to_end_cli_init_and_stats(tmp_path):
    """End-to-end: init a data dir and run stats through the installed CLI."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["stats", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    import json as _json
    payload = _json.loads(r.output)
    assert payload["indexed_pages"] == 0
    assert payload["interests"] == 0
    assert payload["total_tags"] == 0
