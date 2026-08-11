"""
Content Importer Module
Imports content from multiple formats: JSON, HTML, Markdown, RSS, CSV
"""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any
from xml.etree import ElementTree as ET


class ContentImporter:
    """Imports content items from various formats."""

    SUPPORTED_FORMATS = ("json", "html", "markdown", "rss", "csv")

    def __init__(self):
        self._id_counter = 0

    def import_content(self, data: str, fmt: str) -> list[dict[str, Any]]:
        """Import content from the given string data in the specified format."""
        fmt = fmt.lower().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {fmt}. Supported: {self.SUPPORTED_FORMATS}")
        handler = getattr(self, f"_import_{fmt}")
        result: list[dict[str, Any]] = handler(data)
        return result

    def _import_json(self, data: str) -> list[dict[str, Any]]:
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            parsed = [parsed]
        return self._normalize_items(parsed)

    def _import_html(self, data: str) -> list[dict[str, Any]]:
        items = []
        # Extract articles
        article_pattern = re.compile(r"<article[^>]*>(.*?)</article>", re.DOTALL | re.IGNORECASE)
        for match in article_pattern.finditer(data):
            article_html = match.group(1)
            item = self._parse_html_article(article_html)
            items.append(item)
        # Fallback: extract h2 + p pairs
        if not items:
            h2_pattern = re.compile(r"<h2[^>]*>(.*?)</h2>", re.DOTALL | re.IGNORECASE)
            p_pattern = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
            headings = h2_pattern.findall(data)
            paragraphs = p_pattern.findall(data)
            for i, heading in enumerate(headings):
                clean = re.sub(r"<[^>]+>", "", heading).strip()
                desc = paragraphs[i].strip() if i < len(paragraphs) else ""
                items.append({"title": clean, "description": desc, "id": str(self._next_id())})
        return items

    def _parse_html_article(self, html_str: str) -> dict[str, Any]:
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", html_str, re.DOTALL | re.IGNORECASE)
        p = re.search(r"<p[^>]*>(.*?)</p>", html_str, re.DOTALL | re.IGNORECASE)
        a = re.search(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html_str, re.DOTALL | re.IGNORECASE)
        title = re.sub(r"<[^>]+>", "", h2.group(1)).strip() if h2 else "Untitled"
        desc = re.sub(r"<[^>]+>", "", p.group(1)).strip() if p else ""
        link = a.group(1) if a else ""
        return {"title": title, "description": desc, "link": link, "id": str(self._next_id())}

    def _import_markdown(self, data: str) -> list[dict[str, Any]]:
        items = []
        lines = data.split("\n")
        current_item: dict[str, Any] | None = None
        desc_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            # Section heading (## or ###)
            heading_match = re.match(r"^#{1,6}\s+(?:\[(.+)\]\((.+)\)|(.+))$", stripped)
            if heading_match:
                if current_item:
                    current_item["description"] = "\n".join(desc_lines).strip()
                    items.append(current_item)
                    desc_lines = []
                link_text, link_url, plain_title = heading_match.groups()
                title = link_text or plain_title
                link = link_url or ""
                current_item = {"title": title, "link": link, "id": str(self._next_id())}
            elif current_item and stripped and not stripped.startswith("#"):
                desc_lines.append(stripped)

        if current_item:
            current_item["description"] = "\n".join(desc_lines).strip()
            items.append(current_item)
        return items

    def _import_rss(self, data: str) -> list[dict[str, Any]]:
        items = []
        root = ET.fromstring(data)
        for channel in root.findall(".//channel"):
            for item in channel.findall("item"):
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                guid_el = item.find("guid")
                item.find("pubDate")
                title = title_el.text if title_el is not None and title_el.text else "Untitled"
                link = link_el.text if link_el is not None and link_el.text else ""
                desc = desc_el.text if desc_el is not None and desc_el.text else ""
                guid = guid_el.text if guid_el is not None and guid_el.text else str(self._next_id())
                items.append({
                    "title": title,
                    "description": desc,
                    "link": link,
                    "id": guid,
                })
        return items

    def _import_csv(self, data: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(data))
        items = []
        for row in reader:
            item = {k: v for k, v in row.items() if v}
            item.setdefault("id", str(self._next_id()))
            items.append(item)
        return items

    def _normalize_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized = {
                "title": item.get("title", "Untitled"),
                "description": item.get("description", ""),
                "link": item.get("link", ""),
                "id": item.get("id", str(self._next_id())),
                "tags": item.get("tags", []),
                "date": item.get("date"),
            }
            result.append(normalized)
        return result

    def _next_id(self) -> int:
        self._id_counter += 1
        result: int = self._id_counter
        return result

    def batch_import(self, data_sources):
        """Import from multiple data sources.
        data_sources: list of (data_str, format) tuples
        """
        all_items = []
        for data, fmt in data_sources:
            items = self.import_content(data, fmt)
            all_items.extend(items)
        return all_items

