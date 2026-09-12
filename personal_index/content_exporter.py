"""
Content Exporter Module
Exports content to multiple formats: HTML, JSON, Markdown, RSS
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any
from xml.sax.saxutils import escape as xml_escape


class ContentExporter:
    """Exports content items to various formats."""

    SUPPORTED_FORMATS = ("html", "json", "markdown", "rss")

    def __init__(self, title: str = "Personal Index", base_url: str = "http://localhost:8000"):
        self.title = title
        self.base_url = base_url.rstrip("/")

    def export(self, items: list[dict[str, Any]], fmt: str) -> str:
        """Export a list of content items to the specified format.

        The format is normalized with ``fmt.lower().strip()`` before use, so
        padded or mixed-case tokens (e.g. ``"JSON "`` / ``" Html"``) are
        accepted. If the normalized format is not one of
        ``SUPPORTED_FORMATS`` (``"html"``, ``"json"``, ``"markdown"``,
        ``"rss"``), a ``ValueError`` is raised before any handler runs.

        Per-format escaping contract:
        - **HTML**: every user-supplied field (title, description, tags, link,
          and the document title) is escaped with ``html.escape`` (escapes
          ``& < > " '``).
        - **RSS**: title, description, link, and guid are escaped with
          ``xml.sax.saxutils.escape`` (escapes only ``& < >`` — **not** the
          quotes ``"``/``'``).
        - **Markdown**: title, link, description, tags, and the document H1
          title are escaped for well-formed Markdown — backslash, ``[``,
          ``]``, ``(``, ``)`` are escaped, newlines are collapsed to spaces,
          and link-target spaces are percent-encoded (``%20``) — so the output
          is well-formed for arbitrary input (no broken link syntax, no stray
          heading or list).
        - **JSON**: fields are serialized verbatim by ``json.dumps`` (no
          escaping beyond JSON's own string rules).

        A caller reading this docstring knows, without reading the source,
        which characters each format sanitizes and which it does not.
        """
        fmt = fmt.lower().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {fmt}. Supported: {self.SUPPORTED_FORMATS}")
        handler = getattr(self, f"_export_{fmt}")
        result: str = handler(items)
        return result

    def _export_json(self, items: list[dict[str, Any]]) -> str:
        return json.dumps(items, indent=2, default=str)

    def _export_html(self, items: list[dict[str, Any]]) -> str:
        return self._render_html(items)

    def _export_markdown(self, items: list[dict[str, Any]]) -> str:
        return self._render_markdown(items)

    def _export_rss(self, items: list[dict[str, Any]]) -> str:
        return self._render_rss(items)

    # --- HTML rendering ---

    def _render_html(self, items: list[dict[str, Any]]) -> str:
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

    def _html_item(self, item: dict[str, Any]) -> str:
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

    def _render_markdown(self, items: list[dict[str, Any]]) -> str:
        lines = [f"# {self._md_escape(self.title)}", ""]
        for item in items:
            lines.append(self._md_item(item))
        return "\n".join(lines)

    def _md_escape(self, text: str) -> str:
        """Escape Markdown-significant characters for inline use.

        Backslash is escaped first, then ``[``, ``]``, ``(``, ``)`` (which
        would otherwise break link/heading syntax), and newlines are collapsed
        to spaces so no stray heading or list is introduced.
        """
        out = text.replace("\\", "\\\\")
        for ch in "[]()":
            out = out.replace(ch, "\\" + ch)
        out = out.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        return out

    def _md_link_target(self, link: str) -> str:
        """Render a link target that stays well-formed for arbitrary input.

        Newlines are collapsed, parentheses and backslashes are escaped, and
        spaces are percent-encoded (``%20``) so the ``(...)`` target syntax is
        never broken.
        """
        target = link.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        target = target.replace("\\", "\\\\")
        for ch in "()":
            target = target.replace(ch, "\\" + ch)
        target = target.replace(" ", "%20")
        return target

    def _md_item(self, item: dict[str, Any]) -> str:
        title = self._md_escape(item.get("title", "Untitled"))
        raw_link = item.get("link", "")
        desc = self._md_escape(item.get("description", ""))
        if desc.startswith("#"):
            desc = "\\" + desc
        date_str = self._format_date(item.get("date"))
        tags = item.get("tags", [])
        tag_str = ", ".join(self._md_escape(t) for t in tags) if tags else ""
        if raw_link:
            heading = f"## [{title}]({self._md_link_target(raw_link)})"
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
            meta.append(f"🏷\ufe0f {tag_str}")
        if meta:
            parts.append(" | ".join(meta))
        parts.append("")
        return "\n".join(parts)

    # --- RSS rendering ---

    def _render_rss(self, items: list[dict[str, Any]]) -> str:
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

    def _rss_item(self, item: dict[str, Any]) -> str:
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

    @staticmethod
    def detect_format(filepath):
        """Detect export format from file extension."""
        ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
        mapping = {"html": "html", "htm": "html", "json": "json", "md": "markdown", "markdown": "markdown", "rss": "rss", "xml": "rss"}
        return mapping.get(ext)
