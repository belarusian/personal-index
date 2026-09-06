"""Content export as CSV for personal-index."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    TSV = "tsv"
    JSON = "json"
    JSON_LINES = "json_lines"


@dataclass
class ExportStats:
    """Statistics about an export operation."""

    total_items: int = 0
    exported_items: int = 0
    columns: int = 0
    format: str = "csv"


class CSVExporter:
    """Exports content items as CSV and other formats."""

    DEFAULT_COLUMNS: ClassVar[list[str]] = [
        "id", "title", "url", "content_type", "created_at",
        "description", "tags", "score", "is_favorite",
    ]

    def __init__(self) -> None:
        """Initialize the CSV exporter."""

    def _apply_filter_sort(
        self, items: list[dict],
        filter_fn: Callable[[dict], bool] | None,
        sort_key: Callable[[dict], Any] | None,
    ) -> list[dict]:
        out = [i for i in items if filter_fn(i)] if filter_fn else items
        return sorted(out, key=sort_key) if sort_key else out

    def _dispatch_format(
        self, filtered: list[dict], columns: list[str], col_map: dict[str, str],
        fmt: ExportFormat, delimiter: str, quoting: int, include_header: bool,
    ) -> str:
        if fmt == ExportFormat.CSV:
            return self._export_csv(filtered, columns, delimiter, quoting, include_header, col_map)
        if fmt == ExportFormat.TSV:
            return self._export_csv(filtered, columns, "\t", quoting, include_header, col_map)
        if fmt == ExportFormat.JSON:
            return self._export_json(filtered, columns, col_map)
        if fmt == ExportFormat.JSON_LINES:
            return self._export_json_lines(filtered, columns, col_map)
        return self._export_csv(filtered, columns, delimiter, quoting, include_header, col_map)

    def export(
        self,
        items: list[dict],
        columns: list[str] | None = None,
        delimiter: str = ",",
        quoting: int = csv.QUOTE_MINIMAL,  # type: ignore[assignment]
        include_header: bool = True,
        column_names: dict[str, str] | None = None,
        filter_fn: Callable[[dict], bool] | None = None,
        sort_key: Callable[[dict], Any] | None = None,
        limit: int | None = None,
        offset: int = 0,
        export_format: ExportFormat = ExportFormat.CSV,
        encoding: str = "utf-8",
    ) -> str:
        """Export items to the specified format."""
        if not items:
            return ""
        filtered = self._apply_filter_sort(items, filter_fn, sort_key)[offset:]
        if limit is not None:
            filtered = filtered[:limit]
        if not filtered:
            return ""
        if columns is None:
            columns = self._get_columns(filtered)
        col_map = column_names or {}
        return self._dispatch_format(filtered, columns, col_map, export_format, delimiter, quoting, include_header)

    def _get_columns(self, items: list[dict]) -> list[str]:
        """Get all unique columns from items."""
        columns: set[str] = set()
        for item in items:
            columns.update(item.keys())
        # Sort for consistent output, preferring default column order
        ordered = []
        for col in self.DEFAULT_COLUMNS:
            if col in columns:
                ordered.append(col)
        for col in sorted(columns):
            if col not in ordered:
                ordered.append(col)
        return ordered

    def _format_value(self, value: Any) -> str:
        """Format a value for CSV output."""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (list, tuple)):
            return "; ".join(str(v) for v in value)
        if isinstance(value, dict):
            return json.dumps(value)
        return str(value)

    def _export_csv(
        self,
        items: list[dict],
        columns: list[str],
        delimiter: str = ",",
        quoting: int = csv.QUOTE_MINIMAL,  # type: ignore[assignment]
        include_header: bool = True,
        column_names: dict[str, str] | None = None,
    ) -> str:
        """Export items as CSV string."""
        col_map = column_names or {}
        output = io.StringIO()
        writer = csv.writer(
            output, delimiter=delimiter, quoting=quoting,  # type: ignore[arg-type]
            lineterminator="\n",
        )

        if include_header:
            header = [col_map.get(col, col) for col in columns]
            writer.writerow(header)

        for item in items:
            row = [self._format_value(item.get(col, "")) for col in columns]
            writer.writerow(row)

        return output.getvalue()

    def _export_json(
        self,
        items: list[dict],
        columns: list[str],
        column_names: dict[str, str] | None = None,
    ) -> str:
        """Export items as JSON array."""
        col_map = column_names or {}
        result = []
        for item in items:
            row = {}
            for col in columns:
                key = col_map.get(col, col)
                row[key] = self._format_value(item.get(col, ""))
            result.append(row)
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _export_json_lines(
        self,
        items: list[dict],
        columns: list[str],
        column_names: dict[str, str] | None = None,
    ) -> str:
        """Export items as JSON Lines (one JSON object per line)."""
        col_map = column_names or {}
        lines = []
        for item in items:
            row = {}
            for col in columns:
                key = col_map.get(col, col)
                row[key] = self._format_value(item.get(col, ""))
            lines.append(json.dumps(row, ensure_ascii=False))
        return "\n".join(lines) + "\n"

    def export_to_file(
        self,
        items: list[dict],
        filepath: str,
        **kwargs,
    ) -> None:
        """Export items to a file."""
        content = self.export(items, **kwargs)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def get_stats(self, items: list[dict]) -> dict:
        """Get export statistics."""
        if not items:
            return {"total_items": 0, "columns": 0, "column_names": []}
        columns: set[str] = set()
        for item in items:
            columns.update(item.keys())
        return {
            "total_items": len(items),
            "columns": len(columns),
            "column_names": sorted(columns),
        }
