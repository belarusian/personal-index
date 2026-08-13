"""Dashboard view components for personal-index admin interface."""

from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DashboardStat:
    """A single dashboard statistic."""

    label: str
    value: Any
    trend: str | None = None
    icon: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "trend": self.trend,
            "icon": self.icon,
        }


@dataclass
class DashboardSection:
    """A section of the dashboard."""

    title: str
    stats: list[DashboardStat] = field(default_factory=list)
    table_data: list[dict[str, Any]] | None = None
    chart_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "stats": [s.to_dict() for s in self.stats],
            "table_data": self.table_data,
            "chart_data": self.chart_data,
        }


@dataclass
class DashboardData:
    """Complete dashboard data model."""

    title: str = "Personal Index Dashboard"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sections: list[DashboardSection] = field(default_factory=list)
    version: str = "0.1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "sections": [s.to_dict() for s in self.sections],
            "version": self.version,
        }


def escape(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(str(text))


DASHBOARD_CSS = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5; color: #333; padding: 20px; }
        .header { background: #1a1a2e; color: white; padding: 20px 30px;
                   border-radius: 8px; margin-bottom: 20px; }
        .header h1 { font-size: 24px; }
        .header .meta { color: #aaa; font-size: 12px; margin-top: 5px; }
        .section { background: white; border-radius: 8px; padding: 20px;
                   margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section h2 { font-size: 18px; margin-bottom: 16px; color: #1a1a2e; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                  gap: 12px; margin-bottom: 16px; }
        .stat { background: #f8f9fa; padding: 16px; border-radius: 6px; text-align: center; }
        .stat .value { font-size: 28px; font-weight: bold; color: #1a1a2e; }
        .stat .label { font-size: 12px; color: #666; margin-top: 4px; }
        .stat .trend { font-size: 11px; margin-top: 4px; }
        .trend.up { color: #28a745; }
        .trend.down { color: #dc3545; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-size: 12px; text-transform: uppercase; color: #666; }
        td { font-size: 14px; }
        tr:hover { background: #f8f9fa; }
"""


def render_dashboard_html(data: DashboardData) -> str:
    """Render dashboard data as HTML."""
    sections_html = "".join(_render_section(s) for s in data.sections)
    header = _render_header(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(data.title)}</title>
    <style>
{DASHBOARD_CSS}
    </style>
</head>
<body>
    {header}
    {sections_html}
</body>
</html>"""


def _render_header(data: DashboardData) -> str:
    """Render the dashboard header section."""
    return (
        f'<div class="header">\n'
        f"    <h1>{escape(data.title)}</h1>\n"
        f"    <div class=\"meta\">Generated: {escape(data.generated_at)} "
        f"| v{escape(data.version)}</div>\n"
        f"</div>"
    )


def _render_section(section: DashboardSection) -> str:
    """Render a single dashboard section as HTML."""
    stats_html = ""
    for stat in section.stats:
        trend_class = "up" if stat.trend and "+" in str(stat.trend) else "down"
        trend_html = f'<div class="trend {trend_class}">{escape(stat.trend)}</div>' if stat.trend else ""
        stats_html += f"""
        <div class="stat">
            <div class="value">{escape(stat.value)}</div>
            <div class="label">{escape(stat.label)}</div>
            {trend_html}
        </div>"""

    table_html = ""
    if section.table_data:
        headers = section.table_data[0].keys() if section.table_data else []
        header_row = "".join(f"<th>{escape(h)}</th>" for h in headers)
        rows = ""
        for row in section.table_data:
            cells = "".join(f"<td>{escape(str(row.get(h, '')))}</td>" for h in headers)
            rows += f"<tr>{cells}</tr>"
        table_html = f"<table><thead><tr>{header_row}</tr></thead><tbody>{rows}</tbody></table>"

    return f"""
    <div class="section">
        <h2>{escape(section.title)}</h2>
        <div class="stats">{stats_html}</div>
        {table_html}
    </div>"""


def build_dashboard(
    index_instance=None,
    search_index=None,
    config=None,
) -> DashboardData:
    """Build dashboard data from index instances."""
    sections: list[DashboardSection] = []
    sections.append(_build_overview(index_instance))

    if index_instance:
        pages = index_instance.get_all_pages() if hasattr(index_instance, "get_all_pages") else []
        sections.append(_build_recent_pages(pages))
        sections.append(_build_top_domains(pages))

    return DashboardData(sections=sections)


def _build_overview(index_instance: Any) -> DashboardSection:
    """Build the overview section with summary stats."""
    stats = [DashboardStat(label="Status", value="Active", icon="pulse")]
    if index_instance:
        pages = index_instance.get_all_pages() if hasattr(index_instance, "get_all_pages") else []
        stats.append(DashboardStat(label="Total Pages", value=len(pages)))
        domains = {p.domain for p in pages if p.domain}
        stats.append(DashboardStat(label="Unique Domains", value=len(domains)))
        interests = getattr(index_instance, "interests", [])
        stats.append(DashboardStat(label="Active Interests", value=len(interests)))
    return DashboardSection(title="Overview", stats=stats)


def _build_recent_pages(pages: list[Any]) -> DashboardSection:
    """Build the recent pages section with a table."""
    recent = sorted(pages, key=lambda p: p.crawled_at or "", reverse=True)[:10]
    table_data = [
        {
            "URL": p.url,
            "Title": p.title[:50] if p.title else "",
            "Domain": p.domain,
            "Status": p.status_code,
            "Crawled": p.crawled_at[:19] if p.crawled_at else "",
        }
        for p in recent
    ]
    return DashboardSection(title="Recent Pages", table_data=table_data)


def _build_top_domains(pages: list[Any]) -> DashboardSection:
    """Build the top domains section with a table."""
    domain_counts: dict[str, int] = {}
    for p in pages:
        if p.domain:
            domain_counts[p.domain] = domain_counts.get(p.domain, 0) + 1
    top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    domain_table = [{"Domain": d, "Pages": c} for d, c in top_domains]
    return DashboardSection(title="Top Domains", table_data=domain_table)
