"""CSV export functionality for personal-index content.

Exports content items to CSV format with configurable columns,
delimiters, and encoding options.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CsvExportOptions:
    """Options for CSV export.

    Attributes:
        delimiter: Column delimiter character.
        quotechar: Quote character for fields.
        quoting: CSV quoting mode.
        encoding: File encoding.
        include_header: Whether to include header row.
        columns: Specific columns to include (None for all).
        flatten_nested: Whether to flatten nested dicts.
        separator_nested: Separator for flattened nested keys.
    """

    delimiter: str = ","
    quotechar: str = '"'
    quoting: int = csv.QUOTE_NONNUMERIC
    encoding: str = "utf-8"
    include_header: bool = True
    columns: list[str] | None = None
    flatten_nested: bool = True
    separator_nested: str = "."


class CsvExporter:
    """Exports content data to CSV format.

    Handles nested data structures, date formatting, and
    configurable column selection.
    """

    def __init__(self, options: CsvExportOptions | None = None) -> None:
        self.options = options or CsvExportOptions()

    def export_items(self, items: list[dict[str, Any]]) -> str:
        """Export items to CSV string.

        Args:
            items: List of content item dictionaries.

        Returns:
            CSV string representation.
        """
        if not items:
            return ""

        output = io.StringIO()
        processed = [self._process_item(item) for item in items]
        columns = self._get_columns(processed)

        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            delimiter=self.options.delimiter,
            quotechar=self.options.quotechar,
            quoting=self.options.quoting,
        )

        if self.options.include_header:
            writer.writeheader()

        for item in processed:
            row = {col: item.get(col, "") for col in columns}
            writer.writerow(row)

        return output.getvalue()

    def export_to_file(
        self,
        items: list[dict[str, Any]],
        filepath: str | Path,
    ) -> int:
        """Export items to a CSV file.

        Args:
            items: List of content item dictionaries.
            filepath: Path to the output file.

        Returns:
            Number of items exported.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.export_items(items)
        filepath.write_text(content, encoding=self.options.encoding)
        return len(items)

    def _process_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Process a single item for CSV export."""
        result: dict[str, Any] = {}
        for key, value in item.items():
            if self.options.flatten_nested and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat_key = (
                        f"{key}{self.options.separator_nested}{sub_key}"
                    )
                    result[flat_key] = self._format_value(sub_value)
            else:
                result[key] = self._format_value(value)
        return result

    def _format_value(self, value: Any) -> Any:
        """Format a value for CSV output.

        Returns numbers for numeric strings so QUOTE_NONNUMERIC
        doesn't quote them, while empty strings (from None) stay
        as strings and get quoted.
        """
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (list, set)):
            return "; ".join(str(v) for v in value)
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, str):
            # Convert numeric strings to numbers so QUOTE_NONNUMERIC
            # doesn't add unnecessary quotes around them
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    pass
        return str(value)

    def _get_columns(
        self,
        items: list[dict[str, Any]],
    ) -> list[str]:
        """Determine columns from items."""
        all_columns = set()
        for item in items:
            all_columns.update(item.keys())

        if self.options.columns:
            return [
                c for c in self.options.columns
                if c in all_columns
            ]
        return sorted(all_columns)
