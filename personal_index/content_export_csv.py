"""Content export as CSV for personal-index."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


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

    DEFAULT_COLUMNS = [
        "id", "title", "url", "content_type", "created_at",
        "description", "tags", "score", "is_favorite",
    ]

    def __init__(self) -> None:
        pass

    def export(
        self,
        items: list[dict],
        columns: Optional[list[str]] = None,
        delimiter: str = ",",
        quoting: int = csv.QUOTE_MINIMAL,
        include_header: bool = True,
        column_names: Optional[dict[str, str]] = None,
        filter_fn: Optional[Callable[[dict], bool]] = None,
        sort_key: Optional[Callable[[dict], Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        format: ExportFormat = ExportFormat.CSV,
        encoding: str = "utf-8",
    ) -> str:
        """Export items to the specified format."""
        if not items:
            return ""

        # Apply filters and sorting
        filtered = items
        if filter_fn:
            filtered = [item for item in items if filter_fn(item)]

        if sort_key:
            filtered = sorted(filtered, key=sort_key)

        # Apply pagination
        filtered = filtered[offset:]
        if limit is not None:
            filtered = filtered[:limit]

        if not filtered:
            return ""

        # Determine columns
        if columns is None:
            columns = self._get_columns(filtered)

        # Apply column name mapping
        col_map = column_names or {}

        if format == ExportFormat.CSV:
            return self._export_csv(
                filtered, columns, delimiter=delimiter,
                quoting=quoting, include_header=include_header,
                column_names=col_map,
            )
        elif format == ExportFormat.TSV:
            return self._export_csv(
                filtered, columns, delimiter="\t",
                quoting=quoting, include_header=include_header,
                column_names=col_map,
            )
        elif format == ExportFormat.JSON:
            return self._export_json(filtered, columns, col_map)
        elif format == ExportFormat.JSON_LINES:
            return self._export_json_lines(filtered, columns, col_map)
        else:
            return self._export_csv(
                filtered, columns, delimiter=delimiter,
                quoting=quoting, include_header=include_header,
                column_names=col_map,
            )

    def _get_columns(self, items: list[dict]) -> list[str]:
        """Get all unique columns from items."""
        columns = set()
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
        quoting: int = csv.QUOTE_MINIMAL,
        include_header: bool = True,
        column_names: Optional[dict[str, str]] = None,
    ) -> str:
        """Export items as CSV string."""
        col_map = column_names or {}
        output = io.StringIO()
        writer = csv.writer(
            output, delimiter=delimiter, quoting=quoting,
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
        column_names: Optional[dict[str, str]] = None,
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
        column_names: Optional[dict[str, str]] = None,
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
            return {"total_items": 0, "columns": 0}
        columns = set()
        for item in items:
            columns.update(item.keys())
        return {
            "total_items": len(items),
            "columns": len(columns),
            "column_names": sorted(columns),
        }
