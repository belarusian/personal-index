"""Export functionality for the admin dashboard."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, cast


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    TSV = "tsv"


@dataclass
class ExportResult:
    """Result of an export operation."""
    format: str
    content: str
    filename: str
    row_count: int = 0
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "filename": self.filename,
            "row_count": self.row_count,
            "generated_at": self.generated_at,
            "content_length": len(self.content),
        }


class DashboardExporter:
    """Exports dashboard data in various formats."""

    def __init__(self):
        self._headers: list[str] = []

    def export_stats(
        self,
        stats: Any,
        fmt: ExportFormat = ExportFormat.JSON,
        filename: str | None = None,
    ) -> ExportResult:
        """Export aggregated stats to a format.

        Args:
            stats: Stats object or dict to export.
            fmt: Export format.
            filename: Optional filename override.

        Returns:
            ExportResult with content and metadata.
        """
        if hasattr(stats, "to_dict"):
            data = stats.to_dict()
        elif isinstance(stats, dict):
            data = stats
        else:
            data = asdict(stats)

        if fmt == ExportFormat.JSON:
            content = json.dumps(data, indent=2, default=str)
            fname = filename or "dashboard_stats.json"
        elif fmt == ExportFormat.CSV:
            content = self._dict_to_csv([data])
            fname = filename or "dashboard_stats.csv"
        elif fmt == ExportFormat.TSV:
            content = self._dict_to_tsv([data])
            fname = filename or "dashboard_stats.tsv"
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return ExportResult(format=fmt.value, content=content, filename=fname)

    def export_pages(
        self,
        pages: list[Any],
        fmt: ExportFormat = ExportFormat.CSV,
        filename: str | None = None,
        fields: list[str] | None = None,
    ) -> ExportResult:
        """Export pages list to a format."""
        rows = [self._page_to_dict(p, fields) for p in pages]
        content, fname = self._format_output(rows, fmt, filename or "pages_export")
        return ExportResult(format=fmt.value, content=content, filename=fname, row_count=len(rows))

    @staticmethod
    def _page_to_dict(page: Any, fields: list[str] | None) -> dict[str, Any]:
        """Convert a page object to a dict, optionally filtering fields."""
        if hasattr(page, "to_dict"):
            row = cast(dict[str, Any], page.to_dict())
        elif isinstance(page, dict):
            row = page
        else:
            row = asdict(page)
        if fields:
            row = {k: row.get(k, "") for k in fields}
        return row

    def _format_output(
        self, rows: list[dict[str, Any]], fmt: ExportFormat, base_name: str
    ) -> tuple[str, str]:
        """Format rows and return (content, filename) for the given format."""
        if fmt == ExportFormat.JSON:
            return json.dumps(rows, indent=2, default=str), f"{base_name}.json"
        if fmt == ExportFormat.CSV:
            return self._dict_to_csv(rows), f"{base_name}.csv"
        if fmt == ExportFormat.TSV:
            return self._dict_to_tsv(rows), f"{base_name}.tsv"
        raise ValueError(f"Unsupported format: {fmt}")

    def export_time_series(
        self,
        series: list[Any],
        fmt: ExportFormat = ExportFormat.CSV,
        filename: str | None = None,
    ) -> ExportResult:
        """Export time series data."""
        rows = self._points_to_rows(series)
        content, fname = self._format_output(rows, fmt, filename or "timeseries")
        return ExportResult(
            format=fmt.value, content=content, filename=fname, row_count=len(rows),
        )

    @staticmethod
    def _points_to_rows(series: list[Any]) -> list[dict[str, Any]]:
        """Convert time series points to list of dicts."""
        rows: list[dict[str, Any]] = []
        for point in series:
            if hasattr(point, "to_dict"):
                rows.append(point.to_dict())
            elif isinstance(point, dict):
                rows.append(point)
            else:
                rows.append(asdict(point))
        return rows

    @staticmethod
    def _dict_to_csv(rows: list[dict[str, Any]]) -> str:
        """Convert list of dicts to CSV string."""
        if not rows:
            return ""
        output = io.StringIO()
        headers = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # Flatten nested dicts
            flat_row = {}
            for k, v in row.items():
                if isinstance(v, dict):
                    for nk, nv in v.items():
                        flat_row[f"{k}.{nk}"] = nv
                elif isinstance(v, list):
                    flat_row[k] = "; ".join(str(x) for x in v)
                else:
                    flat_row[k] = v
            writer.writerow(flat_row)
        return output.getvalue()

    @staticmethod
    def _dict_to_tsv(rows: list[dict[str, Any]]) -> str:
        """Convert list of dicts to TSV string."""
        if not rows:
            return ""
        output = io.StringIO()
        headers = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat_row = {}
            for k, v in row.items():
                if isinstance(v, dict):
                    for nk, nv in v.items():
                        flat_row[f"{k}.{nk}"] = nv
                elif isinstance(v, list):
                    flat_row[k] = "; ".join(str(x) for x in v)
                else:
                    flat_row[k] = v
            writer.writerow(flat_row)
        return output.getvalue()
