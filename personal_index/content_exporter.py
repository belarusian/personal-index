"""
Content Exporter Module
Exports content to multiple formats: HTML, JSON, Markdown, RSS
"""

from __future__ import annotations

import json
import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as xml_escape


class ContentExporter:
    """Exports content items to various formats."""

    SUPPORTED_FORMATS = ("html", "json", "markdown", "rss")

    def __init__(self, title: str = "Personal Index", base_url: str = "http://localhost:8000"):
        self.title = title
        self.base_url = base_url.rstrip("/")

    def export(self, items: List[Dict[str, Any]], fmt: str) -> str:
        """Export a list of content items to the specified format."""
        fmt = fmt.lower().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {fmt}. Supported: {self.SUPPORTED_FORMATS}")
        handler = getattr(self, f"_export_{fmt}")
        return handler(items)

    def _export_json(self, items: List[Dict[str, Any]]) -> str:
        return json.dumps(items, indent=2, default=str)

    def _export_html(self, items: List[Dict[str, Any]]) -> str:
        return self._render_html(items)

    def _export_markdown(self, items: List[Dict[str, Any]]) -> str:
        return self._render_markdown(items)

    def _export_rss(self, items: List[Dict[str, Any]]) -> str:
        return self._render_rss(items)

    # --- HTML rendering ---

    def _render_html(self, items: List[Dict[str, Any]]) -> str:
        parts = [
            "<!DOCTYPE html>",
            "<html lang=\"en\">",
            "<head>",
            f"<title>{html.escape(self.title)}</title>",
            "<meta charset=\"utf-8\">",
            "<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:1rem}",
            "article{border-bottom:1px solid #ccc;padding:1rem 0}",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{html.escape(self.title)}</h1>",
        ]
        for item in items:
            parts.append(self._html_item(item))
        parts.append("</body></html>")
        return "\n".join(parts)

    def _html_item(self, item: Dict[str, Any]) -> str:
        title = html.escape(item.get("title", "Untitled"))
        desc = html.escape(item.get("description", ""))
        link = item.get("link", "")
        date_str = self._format_date(item.get("date"))
        tags = item.get("tags", [])
        tag_html = " ".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
        href = f'href="{html.escape(link)}"' if link else ""
        return (
            f"<article>"
            f"<h2><a {href}>{title}</a></h2>"
            f"<p>{desc}</p>"
            f"<small>{date_str} | {tag_html}</small>"
            f"</article>"
        )

    # --- Markdown rendering ---

    def _render_markdown(self, items: List[Dict[str, Any]]) -> str:
        lines = [f"# {self.title}", ""]
        for item in items:
            lines.append(self._md_item(item))
        return "\n".join(lines)

    def _md_item(self, item: Dict[str, Any]) -> str:
        title = item.get("title", "Untitled")
        link = item.get("link", "")
        desc = item.get("description", "")
        date_str = self._format_date(item.get("date"))
        tags = item.get("tags", [])
        tag_str = ", ".join(tags) if tags else ""
        if link:
            heading = f"## [{title}]({link})"
        else:
            heading = f"## {title}"
        parts = [heading, ""]
        if desc:
            parts.append(desc)
            parts.append("")
        meta = []
        if date_str:
            meta.append(f"📅 {date_str}")
        if tag_str:
            meta.append(f"🏷️ {tag_str}")
        if meta:
            parts.append(" | ".join(meta))
        parts.append("")
        return "\n".join(parts)

    # --- RSS rendering ---

    def _render_rss(self, items: List[Dict[str, Any]]) -> str:
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<rss version=\"2.0\">",
            "<channel>",
            f"<title>{xml_escape(self.title)}</title>",
            f"<link>{xml_escape(self.base_url)}</link>",
            f"<description>{xml_escape(self.title)}</description>",
            f"<lastBuildDate>{now}</lastBuildDate>",
        ]
        for item in items:
            lines.append(self._rss_item(item))
        lines.append("</channel></rss>")
        return "\n".join(lines)

    def _rss_item(self, item: Dict[str, Any]) -> str:
        title = xml_escape(item.get("title", "Untitled"))
        desc = xml_escape(item.get("description", ""))
        link = xml_escape(item.get("link", self.base_url))
        date_str = self._format_rss_date(item.get("date"))
        guid = xml_escape(item.get("id", link))
        return (
            "<item>"
            f"<title>{title}</title>"
            f"<link>{link}</link>"
            f"<description>{desc}</description>"
            f"<guid>{guid}</guid>"
            f"<pubDate>{date_str}</pubDate>"
            "</item>"
        )

    # --- Helpers ---

    def _format_date(self, date_val: Any) -> str:
        if date_val is None:
            return ""
        if isinstance(date_val, datetime):
            return date_val.strftime("%Y-%m-%d")
        return str(date_val)

    def export_to_file(self, items, fmt, filepath):
        """Export items to a file."""
        content = self.export(items, fmt)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath


    def _format_rss_date(self, date_val: Any) -> str:
        if date_val is None:
            return ""
        if isinstance(date_val, datetime):
            return date_val.strftime("%a, %d %b %Y %H:%M:%S +0000")
        return str(date_val)

    def export_to_file(self, items, fmt, filepath):
        """Export items to a file."""
        content = self.export(items, fmt)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

