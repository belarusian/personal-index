"""Export saved content as plain text.

Provides configurable plain text export of content items with support for
multiple output styles, field filtering, sorting, and pagination.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, List, Optional


class TXTExportStyle(str, Enum):
    """Supported plain text export styles."""

    PLAIN = "plain"
    MARKDOWN = "markdown"

    @classmethod
    def from_string(cls, value: str) -> "TXTExportStyle":
        """Create a style from a string, defaulting to PLAIN on unknown values."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.PLAIN


@dataclass
class TXTExportConfig:
    """Configuration for plain text export."""

    title: str = "Content Export"
    include_title: bool = True
    include_url: bool = True
    include_date: bool = True
    include_tags: bool = True
    include_description: bool = True
    include_body: bool = True
    separator: str = "=" * 60
    item_separator: str = "-" * 40
    max_line_length: int = 80
    wrap_text: bool = True
    encoding: str = "utf-8"
    style: TXTExportStyle = TXTExportStyle.PLAIN
    sort_by: Optional[str] = None
    sort_reverse: bool = False
    limit: Optional[int] = None
    offset: int = 0
    include_fields: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None

    def to_dict(self) -> dict:
        """Serialize config to a dictionary."""
        return {
            "title": self.title,
            "include_title": self.include_title,
            "include_url": self.include_url,
            "include_date": self.include_date,
            "include_tags": self.include_tags,
            "include_description": self.include_description,
            "include_body": self.include_body,
            "separator": self.separator,
            "item_separator": self.item_separator,
            "max_line_length": self.max_line_length,
            "wrap_text": self.wrap_text,
            "encoding": self.encoding,
            "style": self.style.value,
            "sort_by": self.sort_by,
            "sort_reverse": self.sort_reverse,
            "limit": self.limit,
            "offset": self.offset,
            "include_fields": self.include_fields,
            "exclude_fields": self.exclude_fields,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TXTExportConfig":
        """Create a config from a dictionary."""
        style_value = data.get("style", "plain")
        if isinstance(style_value, TXTExportStyle):
            style = style_value
        else:
            style = TXTExportStyle.from_string(str(style_value))
        return cls(
            title=data.get("title", "Content Export"),
            include_title=data.get("include_title", True),
            include_url=data.get("include_url", True),
            include_date=data.get("include_date", True),
            include_tags=data.get("include_tags", True),
            include_description=data.get("include_description", True),
            include_body=data.get("include_body", True),
            separator=data.get("separator", "=" * 60),
            item_separator=data.get("item_separator", "-" * 40),
            max_line_length=data.get("max_line_length", 80),
            wrap_text=data.get("wrap_text", True),
            encoding=data.get("encoding", "utf-8"),
            style=style,
            sort_by=data.get("sort_by"),
            sort_reverse=data.get("sort_reverse", False),
            limit=data.get("limit"),
            offset=data.get("offset", 0),
            include_fields=data.get("include_fields"),
            exclude_fields=data.get("exclude_fields"),
        )


@dataclass
class TXTExportResult:
    """Result of a plain text export operation."""

    items_exported: int = 0
    output: str = ""
    errors: List[str] = field(default_factory=list)
    exported_at: str = ""
    style: str = "plain"

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Serialize result to a dictionary."""
        return {
            "items_exported": self.items_exported,
            "output": self.output,
            "errors": self.errors,
            "exported_at": self.exported_at,
            "style": self.style,
        }


class TXTExporter:
    """Export content items to plain text format."""

    # Fields that represent the body/content of an item
    BODY_FIELDS = ("body", "content", "text")

    def _format_date(self, value: Any) -> str:
        """Format a date value for display."""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, str):
            # Try to extract date portion from ISO format strings
            return value.split("T")[0] if "T" in value else value
        return str(value)

    def _format_tags(self, tags: Any) -> str:
        """Format tags for display."""
        if tags is None:
            return ""
        if isinstance(tags, (list, tuple)):
            return ", ".join(str(t) for t in tags)
        return str(tags)

    def _get_body(self, item: dict) -> str:
        """Extract body text from an item, checking multiple field names."""
        for field_name in self.BODY_FIELDS:
            value = item.get(field_name)
            if value is not None and str(value).strip():
                return str(value)
        return ""

    def _get_field(self, item: dict, field_name: str) -> Optional[str]:
        """Get a field value from an item, returning None if missing."""
        value = item.get(field_name)
        if value is None:
            return None
        return str(value)

    def _get_date(self, item: dict) -> Optional[Any]:
        """Get the best available date from an item (updated_at preferred, then created_at)."""
        if item.get("updated_at") is not None:
            return item["updated_at"]
        if item.get("created_at") is not None:
            return item["created_at"]
        return None

    def _prepare_items(
        self,
        items: List[dict],
        config: TXTExportConfig,
        filter_fn: Optional[Callable[[dict], bool]] = None,
        sort_key: Optional[Callable[[dict], Any]] = None,
    ) -> List[dict]:
        """Apply filtering, sorting, and pagination to items."""
        result = items[:]

        # Apply custom filter
        if filter_fn:
            result = [item for item in result if filter_fn(item)]

        # Apply sorting: custom sort_key takes precedence over config.sort_by
        if sort_key:
            result = sorted(result, key=sort_key)
        elif config.sort_by:
            result = sorted(
                result,
                key=lambda x: (
                    x.get(config.sort_by) is None,
                    str(x.get(config.sort_by, "")),
                ),
                reverse=config.sort_reverse,
            )

        # Apply offset and limit
        result = result[config.offset:]
        if config.limit is not None:
            result = result[: config.limit]

        return result

    def _format_item_plain(self, item: dict, config: TXTExportConfig) -> str:
        """Format a single item in plain text style."""
        lines: List[str] = []

        if config.include_title:
            title = self._get_field(item, "title") or "Untitled"
            lines.append(title)

        if config.include_url:
            url = self._get_field(item, "url")
            if url:
                lines.append(f"URL: {url}")

        if config.include_date:
            date_val = self._get_date(item)
            if date_val is not None:
                lines.append(f"Date: {self._format_date(date_val)}")

        if config.include_description:
            desc = self._get_field(item, "description")
            if desc:
                lines.append(f"Description: {desc}")

        if config.include_tags:
            tags = item.get("tags")
            if tags is not None:
                formatted_tags = self._format_tags(tags)
                if formatted_tags:
                    lines.append(f"Tags: {formatted_tags}")

        if config.include_body:
            body = self._get_body(item)
            if body:
                lines.append("")
                if config.wrap_text and config.max_line_length:
                    wrapped = textwrap.fill(
                        body,
                        width=config.max_line_length,
                        replace_whitespace=True,
                    )
                    lines.append(wrapped)
                else:
                    lines.append(body)

        return "\n".join(lines)

    def _format_item_markdown(self, item: dict, config: TXTExportConfig) -> str:
        """Format a single item in markdown style."""
        lines: List[str] = []

        if config.include_title:
            title = self._get_field(item, "title") or "Untitled"
            lines.append(f"# {title}")

        if config.include_url:
            url = self._get_field(item, "url")
            if url:
                lines.append(f"[{url}]({url})")

        if config.include_date:
            date_val = self._get_date(item)
            if date_val is not None:
                lines.append(f"*{self._format_date(date_val)}*")

        if config.include_description:
            desc = self._get_field(item, "description")
            if desc:
                lines.append(f"> {desc}")

        if config.include_tags:
            tags = item.get("tags")
            if tags is not None:
                formatted_tags = self._format_tags(tags)
                if formatted_tags:
                    lines.append(f"`{formatted_tags}`")

        if config.include_body:
            body = self._get_body(item)
            if body:
                lines.append("")
                if config.wrap_text and config.max_line_length:
                    wrapped = textwrap.fill(
                        body,
                        width=config.max_line_length,
                        replace_whitespace=True,
                    )
                    lines.append(wrapped)
                else:
                    lines.append(body)

        return "\n".join(lines)

    def _format_item(self, item: dict, config: TXTExportConfig) -> str:
        """Format a single item according to the configured style."""
        if config.style == TXTExportStyle.MARKDOWN:
            return self._format_item_markdown(item, config)
        return self._format_item_plain(item, config)

    def _apply_field_filters(
        self, items: List[dict], config: TXTExportConfig
    ) -> List[dict]:
        """Filter item fields based on include/exclude lists."""
        if not config.include_fields and not config.exclude_fields:
            return items

        result = []
        for item in items:
            filtered = dict(item)
            if config.include_fields:
                filtered = {
                    k: v for k, v in filtered.items() if k in config.include_fields
                }
            if config.exclude_fields:
                filtered = {
                    k: v for k, v in filtered.items() if k not in config.exclude_fields
                }
            result.append(filtered)
        return result

    def export(
        self,
        items: List[dict],
        config: Optional[TXTExportConfig] = None,
        filter_fn: Optional[Callable[[dict], bool]] = None,
        sort_key: Optional[Callable[[dict], Any]] = None,
    ) -> TXTExportResult:
        """Export content items to a plain text string.

        Args:
            items: List of content item dictionaries to export.
            config: Export configuration. Uses defaults if not provided.
            filter_fn: Optional callable to filter items before export.
            sort_key: Optional callable to sort items before export.

        Returns:
            TXTExportResult containing the exported text and metadata.
        """
        if config is None:
            config = TXTExportConfig()

        if not items:
            return TXTExportResult(style=config.style.value)

        try:
            # Apply field-level filtering
            items = self._apply_field_filters(items, config)

            # Prepare items with sorting, filtering, pagination
            prepared = self._prepare_items(items, config, filter_fn, sort_key)

            if not prepared:
                return TXTExportResult(style=config.style.value)

            # Build output
            parts: List[str] = []

            # Add header
            parts.append(config.separator)
            parts.append(config.title)
            parts.append(config.separator)
            parts.append("")

            # Add each item
            for i, item in enumerate(prepared):
                item_text = self._format_item(item, config)
                parts.append(item_text)

                # Add separator between items (not after the last one)
                if i < len(prepared) - 1:
                    parts.append("")
                    parts.append(config.item_separator)
                    parts.append("")

            output = "\n".join(parts)

            return TXTExportResult(
                items_exported=len(prepared),
                output=output,
                style=config.style.value,
            )
        except Exception as e:
            return TXTExportResult(
                items_exported=0,
                errors=[str(e)],
                style=config.style.value,
            )

    def export_to_file(
        self,
        items: List[dict],
        filepath: str,
        config: Optional[TXTExportConfig] = None,
        filter_fn: Optional[Callable[[dict], bool]] = None,
        sort_key: Optional[Callable[[dict], Any]] = None,
    ) -> TXTExportResult:
        """Export content items to a plain text file.

        Args:
            items: List of content item dictionaries to export.
            filepath: Path to the output file.
            config: Export configuration. Uses defaults if not provided.
            filter_fn: Optional callable to filter items before export.
            sort_key: Optional callable to sort items before export.

        Returns:
            TXTExportResult containing the exported text and metadata.
        """
        result = self.export(items, config=config, filter_fn=filter_fn, sort_key=sort_key)
        if result.output:
            encoding = config.encoding if config else "utf-8"
            with open(filepath, "w", encoding=encoding) as f:
                f.write(result.output)
        return result
