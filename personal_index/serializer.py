"""Data serialization utilities for indexed content."""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SerializationError(Exception):
    """Raised when serialization fails."""
    pass


class DeserializationError(Exception):
    """Raised when deserialization fails."""
    pass


@dataclass
class SerializationConfig:
    """Configuration for serialization."""

    indent: int = 2
    ensure_ascii: bool = False
    default_handler: bool = True
    include_none: bool = True


class Serializer:
    """Handles serialization of data to various formats."""

    def __init__(self, config: SerializationConfig | None = None):
        self.config = config or SerializationConfig()

    def to_json(self, data: Any) -> str:
        """Serialize data to JSON string."""
        try:
            return json.dumps(
                self._prepare(data),
                indent=self.config.indent,
                ensure_ascii=self.config.ensure_ascii,
                default=self._default_handler if self.config.default_handler else None,
            )
        except (TypeError, ValueError) as e:
            raise SerializationError(f"Failed to serialize to JSON: {e}")

    def from_json(self, json_str: str) -> dict:
        """Deserialize JSON string to dict."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise DeserializationError(f"Failed to deserialize JSON: {e}")

    def to_csv(self, data: list[dict], include_header: bool = True) -> str:
        """Serialize list of dicts to CSV string."""
        if not data:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys(), extrasaction="ignore")
        if include_header:
            writer.writeheader()
        writer.writerows(self._prepare_row(d) for d in data)
        return output.getvalue()

    def from_csv(self, csv_str: str) -> list[dict]:
        """Deserialize CSV string to list of dicts."""
        if not csv_str.strip():
            return []
        reader = csv.DictReader(io.StringIO(csv_str))
        return [row for row in reader]

    def to_dict(self, obj: Any) -> dict:
        """Convert dataclass or object to dict."""
        if hasattr(obj, "__dataclass_fields__"):
            return self._dataclass_to_dict(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if isinstance(obj, dict):
            return obj
        raise SerializationError(f"Cannot serialize type: {type(obj)}")

    def _dataclass_to_dict(self, obj: Any) -> dict:
        result = {}
        for f in fields(obj):
            value = getattr(obj, f.name)
            if value is None and not self.config.include_none:
                continue
            if hasattr(value, "__dataclass_fields__"):
                result[f.name] = self._dataclass_to_dict(value)
            elif isinstance(value, list):
                result[f.name] = [
                    self._dataclass_to_dict(v) if hasattr(v, "__dataclass_fields__") else v
                    for v in value
                ]
            else:
                result[f.name] = value
        return result

    def _prepare(self, data: Any) -> Any:
        if hasattr(data, "__dataclass_fields__"):
            return self._dataclass_to_dict(data)
        if isinstance(data, dict):
            return {k: self._prepare(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._prepare(item) for item in data]
        return data

    def _prepare_row(self, data: dict) -> dict:
        return {k: str(v) if not isinstance(v, str) else v for k, v in data.items()}

    def _default_handler(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "__dataclass_fields__"):
            return self._dataclass_to_dict(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)
