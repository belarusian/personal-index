"""Export functionality for the admin dashboard."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


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

    def to_dict(self) -> Dict[str, Any]:
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
        self._headers: List[str] = []

    def export_stats(
        self,
        stats: Any,
        fmt: ExportFormat = ExportFormat.JSON,
        filename: Optional[str] = None,
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
        pages: List[Any],
        fmt: ExportFormat = ExportFormat.CSV,
        filename: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> ExportResult:
        """Export pages list to a format.

        Args:
            pages: List of page objects.
            fmt: Export format.
            filename: Optional filename override.
            fields: Optional list of fields to include.

        Returns:
            ExportResult with content and metadata.
        """
        rows = []
        for page in pages:
            if hasattr(page, "to_dict"):
                row = page.to_dict()
            elif isinstance(page, dict):
                row = page
            else:
                row = asdict(page)
            if fields:
                row = {k: row.get(k, "") for k in fields}
            rows.append(row)

        if fmt == ExportFormat.JSON:
            content = json.dumps(rows, indent=2, default=str)
            fname = filename or "pages_export.json"
        elif fmt == ExportFormat.CSV:
            content = self._dict_to_csv(rows)
            fname = filename or "pages_export.csv"
        elif fmt == ExportFormat.TSV:
            content = self._dict_to_tsv(rows)
            fname = filename or "pages_export.tsv"
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return ExportResult(
            format=fmt.value,
            content=content,
            filename=fname,
            row_count=len(rows),
        )

    def export_time_series(
        self,
        series: List[Any],
        fmt: ExportFormat = ExportFormat.CSV,
        filename: Optional[str] = None,
    ) -> ExportResult:
        """Export time series data.

        Args:
            series: List of time series points.
            fmt: Export format.
            filename: Optional filename override.

        Returns:
            ExportResult with content and metadata.
        """
        rows = []
        for point in series:
            if hasattr(point, "to_dict"):
                rows.append(point.to_dict())
            elif isinstance(point, dict):
                rows.append(point)
            else:
                rows.append(asdict(point))

        if fmt == ExportFormat.JSON:
            content = json.dumps(rows, indent=2, default=str)
            fname = filename or "timeseries.json"
        elif fmt == ExportFormat.CSV:
            content = self._dict_to_csv(rows)
            fname = filename or "timeseries.csv"
        elif fmt == ExportFormat.TSV:
            content = self._dict_to_tsv(rows)
            fname = filename or "timeseries.tsv"
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        return ExportResult(
            format=fmt.value,
            content=content,
            filename=fname,
            row_count=len(rows),
        )

    @staticmethod
    def _dict_to_csv(rows: List[Dict[str, Any]]) -> str:
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
    def _dict_to_tsv(rows: List[Dict[str, Any]]) -> str:
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
