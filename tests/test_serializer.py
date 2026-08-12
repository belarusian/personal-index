"""Tests for data serialization utilities."""

from dataclasses import dataclass
from datetime import datetime

import pytest

from personal_index.serializer import (
    DeserializationError,
    SerializationConfig,
    SerializationError,
    Serializer,
)


@dataclass
class _TestItem:
    name: str
    value: int
    timestamp: datetime = None


class TestSerializationConfig:
    def test_defaults(self):
        config = SerializationConfig()
        assert config.indent == 2
        assert config.ensure_ascii is False


class TestSerializer:
    def test_to_json_dict(self):
        s = Serializer()
        result = s.to_json({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_from_json(self):
        s = Serializer()
        data = s.from_json('{"key": "value"}')
        assert data["key"] == "value"

    def test_from_json_invalid(self):
        s = Serializer()
        with pytest.raises(DeserializationError):
            s.from_json("not json")

    def test_to_json_dataclass(self):
        s = Serializer()
        item = _TestItem(name="test", value=42, timestamp=datetime(2024, 1, 1))
        result = s.to_json(item)
        assert "test" in result
        assert "42" in result

    def test_to_csv(self):
        s = Serializer()
        data = [{"name": "a", "value": 1}, {"name": "b", "value": 2}]
        result = s.to_csv(data)
        assert "name" in result
        assert "a" in result
        assert "b" in result

    def test_from_csv(self):
        s = Serializer()
        csv_str = "name,value\na,1\nb,2\n"
        result = s.from_csv(csv_str)
        assert len(result) == 2
        assert result[0]["name"] == "a"

    def test_from_csv_empty(self):
        s = Serializer()
        assert s.from_csv("") == []

    def test_to_dict_dataclass(self):
        s = Serializer()
        item = _TestItem(name="test", value=42)
        result = s.to_dict(item)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_to_dict_plain_dict(self):
        s = Serializer()
        result = s.to_dict({"key": "value"})
        assert result == {"key": "value"}

    def test_to_dict_unsupported(self):
        s = Serializer()
        with pytest.raises(SerializationError):
            s.to_dict(42)

    def test_csv_no_header(self):
        s = Serializer()
        data = [{"name": "a", "value": 1}]
        result = s.to_csv(data, include_header=False)
        assert "name" not in result.split("\n")[0]

    def test_empty_csv(self):
        s = Serializer()
        assert s.to_csv([]) == ""

    def test_nested_dataclass(self):
        @dataclass
        class Inner:
            x: int

        @dataclass
        class Outer:
            inner: Inner

        s = Serializer()
        outer = Outer(inner=Inner(x=10))
        result = s.to_dict(outer)
        assert result["inner"]["x"] == 10

    def test_exclude_none(self):
        s = Serializer(config=SerializationConfig(include_none=False))
        item = _TestItem(name="test", value=42, timestamp=None)
        result = s.to_dict(item)
        assert "timestamp" not in result

    def test_datetime_serialization(self):
        s = Serializer()
        dt = datetime(2024, 6, 15, 12, 30, 0)
        result = s.to_json({"time": dt})
        assert "2024-06-15" in result
