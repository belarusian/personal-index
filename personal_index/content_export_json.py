"""Export content items as JSON in various formats."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JSONExportFormat(Enum):
    """JSON export format options."""
    ARRAY = "array"
    LINES = "lines"
    OBJECT = "object"

    @classmethod
    def from_string(cls, value: str) -> "JSONExportFormat":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.ARRAY


@dataclass
class JSONExportConfig:
    """Configuration for JSON export."""
    pretty_print: bool = True
    include_metadata: bool = False
    encoding: str = "utf-8"
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    sort_by: Optional[str] = None
    sort_reverse: bool = False
    limit: Optional[int] = None
    offset: int = 0
    indent: int = 2

    def to_dict(self) -> dict:
        return {
            "pretty_print": self.pretty_print,
            "include_metadata": self.include_metadata,
            "encoding": self.encoding,
            "include_fields": self.include_fields,
            "exclude_fields": self.exclude_fields,
            "sort_by": self.sort_by,
            "sort_reverse": self.sort_reverse,
            "limit": self.limit,
            "offset": self.offset,
            "indent": self.indent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JSONExportConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class JSONExportResult:
    """Result of a JSON export operation."""
    items_exported: int = 0
    output: Optional[str] = None
    format: str = "array"
    errors: List[str] = field(default_factory=list)
    exported_at: str = ""

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "items_exported": self.items_exported,
            "output": self.output,
            "format": self.format,
            "errors": self.errors,
            "exported_at": self.exported_at,
        }


class JSONExporter:
    """Export content items to JSON format."""

    def _filter_fields(self, item: dict, config: JSONExportConfig) -> dict:
        """Filter item fields based on config."""
        if config.include_fields:
            item = {k: v for k, v in item.items() if k in config.include_fields}
        if config.exclude_fields:
            item = {k: v for k, v in item.items() if k not in config.exclude_fields}
        return item

    def _prepare_items(self, items: List[dict], config: JSONExportConfig) -> List[dict]:
        """Prepare items for export with filtering, sorting, and pagination."""
        result = items[:]

        # Apply offset and limit
        result = result[config.offset:]
        if config.limit is not None:
            result = result[: config.limit]

        # Apply sorting
        if config.sort_by:
            result = sorted(
                result,
                key=lambda x: (x.get(config.sort_by) is None, x.get(config.sort_by, "")),
                reverse=config.sort_reverse,
            )

        # Filter fields
        result = [self._filter_fields(item, config) for item in result]

        return result

    def _build_metadata(self, items: List[dict], config: JSONExportConfig) -> dict:
        """Build metadata object."""
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(items),
            "format": "array",
            "exporter": "personal_index.content_export_json",
        }

    def _export_array(
        self, items: List[dict], config: JSONExportConfig
    ) -> str:
        """Export items as a JSON array."""
        prepared = self._prepare_items(items, config)

        if config.include_metadata:
            output = {
                "metadata": self._build_metadata(items, config),
                "items": prepared,
            }
        else:
            output = prepared

        if config.pretty_print:
            return json.dumps(output, indent=config.indent, ensure_ascii=False)
        return json.dumps(output, ensure_ascii=False, separators=(",", ":"))

    def _export_lines(
        self, items: List[dict], config: JSONExportConfig
    ) -> str:
        """Export items as JSON Lines (one JSON object per line)."""
        prepared = self._prepare_items(items, config)
        lines = []
        for item in prepared:
            lines.append(json.dumps(item, ensure_ascii=False))
        return "\n".join(lines)

    def _export_object(
        self, items: List[dict], config: JSONExportConfig
    ) -> str:
        """Export items as a JSON object keyed by id or index."""
        prepared = self._prepare_items(items, config)
        output = {}
        for i, item in enumerate(prepared):
            key = item.get("id", str(i))
            output[str(key)] = item

        if config.include_metadata:
            output = {
                "metadata": self._build_metadata(items, config),
                "items": output,
            }

        if config.pretty_print:
            return json.dumps(output, indent=config.indent, ensure_ascii=False)
        return json.dumps(output, ensure_ascii=False, separators=(",", ":"))

    def export(
        self,
        items: List[dict],
        config: Optional[JSONExportConfig] = None,
        format: Optional[JSONExportFormat] = None,
    ) -> JSONExportResult:
        """Export items to JSON string."""
        if config is None:
            config = JSONExportConfig()
        if format is None:
            format = JSONExportFormat.ARRAY

        try:
            if format == JSONExportFormat.ARRAY:
                output = self._export_array(items, config)
            elif format == JSONExportFormat.LINES:
                output = self._export_lines(items, config)
            elif format == JSONExportFormat.OBJECT:
                output = self._export_object(items, config)
            else:
                output = self._export_array(items, config)

            prepared = self._prepare_items(items, config)
            return JSONExportResult(
                items_exported=len(prepared),
                output=output,
                format=format.value,
            )
        except Exception as e:
            return JSONExportResult(
                items_exported=0,
                errors=[str(e)],
                format=format.value,
            )

    def export_to_file(
        self,
        items: List[dict],
        filepath: str,
        config: Optional[JSONExportConfig] = None,
        format: Optional[JSONExportFormat] = None,
    ) -> JSONExportResult:
        """Export items to a JSON file."""
        result = self.export(items, config=config, format=format)
        if result.output is not None:
            with open(filepath, "w", encoding=config.encoding if config else "utf-8") as f:
                f.write(result.output)
        return result
