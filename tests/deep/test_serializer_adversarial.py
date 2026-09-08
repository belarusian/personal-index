"""Adversarial deep tests for personal_index.serializer.Serializer.

Contract source: personal_index/serializer.py docstrings. These tests pin the
documented JSON/CSV round-trip behavior, the SerializationConfig knobs
(indent / ensure_ascii / default_handler / include_none), the error-fallback
behavior (SerializationError / DeserializationError), the from_json top-level
"may be any JSON value" contract, the to_dict dataclass/object/dict dispatch,
and one end-to-end CLI run.

Functions armored:
  Serializer.to_json, .from_json, .to_csv, .from_csv, .to_dict,
  SerializationConfig (indent/ensure_ascii/default_handler/include_none).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from personal_index.serializer import (
    DeserializationError,
    SerializationConfig,
    SerializationError,
    Serializer,
)


S = Serializer()


# --- to_json / from_json round-trips ---------------------------------------

def test_json_roundtrip_plain_nested():
    """Nested dict/list/None/bool/float survives a to_json->from_json round-trip."""
    d = {"a": 1, "b": [1, 2], "c": None, "d": "x", "e": True, "f": 1.5}
    assert S.from_json(S.to_json(d)) == d


def test_json_roundtrip_unicode():
    """Non-ASCII text round-trips with default ensure_ascii=False."""
    d = {"u": "héllo — 日本語 — 🚀"}
    assert S.from_json(S.to_json(d)) == d


def test_json_scalars_and_empty():
    """Top-level scalars and empty containers serialize to their JSON form."""
    assert S.to_json({}) == "{}"
    assert S.to_json([]) == "[]"
    assert S.to_json(42) == "42"
    assert S.to_json(None) == "null"
    assert S.to_json(True) == "true"


def test_json_roundtrip_dataclass():
    """A dataclass serializes to its field dict and round-trips."""

    @dataclass
    class Inner:
        x: int
        y: str | None = None

    @dataclass
    class Outer:
        name: str
        inner: Inner
        items: list = field(default_factory=list)
        opt: str | None = None

    o = Outer("n", Inner(1, None), [Inner(2, "a")], None)
    out = S.from_json(S.to_json(o))
    assert out == {
        "name": "n",
        "inner": {"x": 1, "y": None},
        "items": [{"x": 2, "y": "a"}],
        "opt": None,
    }


# --- SerializationConfig: default_handler ----------------------------------

def test_default_handler_datetime_true():
    """default_handler=True renders datetime as its ISO string."""
    out = S.to_json({"t": datetime(2020, 1, 2, 3, 4, 5)})
    assert "2020-01-02T03:04:05" in out


def test_default_handler_datetime_false_raises():
    """default_handler=False leaves datetime unserializable -> SerializationError."""
    s = Serializer(SerializationConfig(default_handler=False))
    try:
        s.to_json({"t": datetime(2020, 1, 2, 3, 4, 5)})
    except SerializationError:
        return
    raise AssertionError("expected SerializationError for datetime without handler")


def test_default_handler_set_true_stringifies():
    """default_handler=True stringifies a set (json cannot natively encode it)."""
    out = S.to_json({"s": {1, 2}})
    assert S.from_json(out)["s"] == "{1, 2}"


def test_default_handler_set_false_raises():
    """default_handler=False -> a set is unserializable -> SerializationError."""
    s = Serializer(SerializationConfig(default_handler=False))
    try:
        s.to_json({"s": {1, 2}})
    except SerializationError:
        return
    raise AssertionError("expected SerializationError for set without handler")


# --- SerializationConfig: ensure_ascii / indent ----------------------------

def test_ensure_ascii_false_keeps_unicode():
    """ensure_ascii=False (default) keeps non-ASCII characters literal."""
    out = S.to_json({"u": "héllo"})
    assert "héllo" in out


def test_ensure_ascii_true_escapes_unicode():
    """ensure_ascii=True escapes non-ASCII characters as \\uXXXX."""
    s = Serializer(SerializationConfig(ensure_ascii=True))
    out = s.to_json({"u": "héllo"})
    assert "\\u00e9" in out
    assert "héllo" not in out


def test_indent_forwarded_to_json_dumps():
    """indent is forwarded to json.dumps (indent=0 still emits newlines)."""
    s = Serializer(SerializationConfig(indent=0))
    out = s.to_json({"a": 1})
    # json.dumps(indent=0) is NOT compact; it still breaks lines.
    assert out == '{\n"a": 1\n}'
    # A larger indent widens the nesting.
    s4 = Serializer(SerializationConfig(indent=4))
    out4 = s4.to_json({"a": {"b": 1}})
    assert '    "a"' in out4


# --- to_csv / from_csv round-trips -----------------------------------------

def test_csv_empty_list_is_empty_string():
    """to_csv([]) returns the empty string (documented)."""
    assert S.to_csv([]) == ""


def test_csv_roundtrip_plain():
    """A list of string-valued dicts round-trips through CSV."""
    rows = [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
    assert S.from_csv(S.to_csv(rows)) == rows


def test_csv_special_chars_roundtrip():
    """Commas, quotes and embedded newlines in values survive the round-trip."""
    rows = [
        {"a": "has,comma", "b": 'has"quote'},
        {"a": "line1\nline2", "b": "plain"},
    ]
    assert S.from_csv(S.to_csv(rows)) == rows


def test_csv_non_string_values_stringified():
    """Non-string values are stringified on write (documented _prepare_row)."""
    out = S.to_csv([{"a": 1, "b": 2.5, "c": True}])
    assert "1" in out and "2.5" in out and "True" in out


def test_csv_none_value_stringified():
    """A None value is stringified to 'None' on write."""
    out = S.to_csv([{"a": None, "b": "x"}])
    assert "None" in out


def test_csv_include_header_false():
    """include_header=False omits the header row."""
    out = S.to_csv([{"a": "1", "b": "2"}], include_header=False)
    assert out == "1,2\r\n"


def test_csv_header_only_roundtrips_to_empty():
    """A header-only CSV deserializes to an empty list."""
    assert S.from_csv("a,b\n") == []


def test_csv_extra_key_in_later_row_ignored():
    """A key present only in a later row is dropped (extrasaction='ignore')."""
    out = S.to_csv([{"a": "1"}, {"a": "2", "b": "X"}])
    # fieldnames come from data[0]; the extra 'b' in row 2 is ignored.
    assert S.from_csv(out) == [{"a": "1"}, {"a": "2"}]


def test_from_csv_empty_and_whitespace():
    """from_csv returns [] for empty and whitespace-only input (documented)."""
    assert S.from_csv("") == []
    assert S.from_csv("   \n  ") == []


def test_from_csv_trailing_newline():
    """A trailing newline does not produce a spurious empty row."""
    assert S.from_csv("a,b\n1,2\n") == [{"a": "1", "b": "2"}]


# --- from_json: top-level value + error fallback ---------------------------

def test_from_json_top_level_non_dict():
    """from_json returns whatever the document contains (list/str/null), not just dicts."""
    assert S.from_json("[1,2,3]") == [1, 2, 3]
    assert S.from_json('"hi"') == "hi"
    assert S.from_json("null") is None
    assert S.from_json("7") == 7


def test_from_json_invalid_raises_deserialization_error():
    """Malformed JSON raises DeserializationError (documented)."""
    try:
        S.from_json("{bad")
    except DeserializationError:
        return
    raise AssertionError("expected DeserializationError for malformed JSON")


def test_from_json_empty_string_raises():
    """An empty string is not valid JSON -> DeserializationError."""
    try:
        S.from_json("")
    except DeserializationError:
        return
    raise AssertionError("expected DeserializationError for empty string")


# --- to_dict dispatch -------------------------------------------------------

def test_to_dict_dataclass():
    """A dataclass converts to its field dict."""

    @dataclass
    class P:
        a: int
        b: str

    assert S.to_dict(P(1, "x")) == {"a": 1, "b": "x"}


def test_to_dict_plain_object():
    """A plain object with __dict__ converts to that dict."""

    class Obj:
        def __init__(self) -> None:
            self.a = 1
            self.b = "x"

    assert S.to_dict(Obj()) == {"a": 1, "b": "x"}


def test_to_dict_dict_passthrough():
    """A dict passes through unchanged."""
    assert S.to_dict({"k": "v"}) == {"k": "v"}


def test_to_dict_non_serializable_raises():
    """A bare scalar (int) has no __dict__/dataclass/dict -> SerializationError."""
    try:
        S.to_dict(42)
    except SerializationError:
        return
    raise AssertionError("expected SerializationError for bare int")


def test_to_dict_include_none_true_keeps_none():
    """include_none=True (default) keeps None fields in the output."""

    @dataclass
    class Q:
        a: int
        b: str | None = None

    assert S.to_dict(Q(1)) == {"a": 1, "b": None}


def test_to_dict_include_none_false_drops_none():
    """include_none=False drops None fields from the output."""
    s = Serializer(SerializationConfig(include_none=False))

    @dataclass
    class Q:
        a: int
        b: str | None = None

    assert s.to_dict(Q(1)) == {"a": 1}


def test_to_dict_nested_dataclass():
    """Nested dataclasses (and lists of dataclasses) recurse correctly."""

    @dataclass
    class Inner:
        x: int
        y: str | None = None

    @dataclass
    class Outer:
        name: str
        inner: Inner
        items: list

    o = Outer("n", Inner(1, None), [Inner(2, "a")])
    assert S.to_dict(o) == {
        "name": "n",
        "inner": {"x": 1, "y": None},
        "items": [{"x": 2, "y": "a"}],
    }


# --- idempotence / property ------------------------------------------------

def test_to_dict_idempotent_on_dict():
    """to_dict is idempotent on a plain dict."""
    d = {"a": {"b": 1}}
    assert S.to_dict(S.to_dict(d)) == d


def test_json_roundtrip_property_randomish():
    """Property: for JSON-safe payloads, from_json(to_json(x)) == x."""
    payloads: list[Any] = [
        {},
        [],
        {"deep": {"deeper": [1, 2, {"x": None}]}},
        {"s": "ünïcodé", "n": -3.14, "b": False},
    ]
    for p in payloads:
        assert S.from_json(S.to_json(p)) == p


# --- end-to-end CLI run -----------------------------------------------------

def test_end_to_end_cli_init_and_export(tmp_path):
    """End-to-end: init + export on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner

    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["export", "--format", "json", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "No indexed content to export." in r.output
