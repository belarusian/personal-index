"""
Output formatting for personal-index.

Provides consistent formatting for CLI output, search results,
and status reports.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SearchResultDisplay:
    """Formatted search result for display."""
    rank: int
    title: str
    url: str
    snippet: str
    score: float
    source_interest: str = ""
    indexed_at: str = ""


def format_search_results(results, limit: int = 20) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."

    lines = []
    for i, result in enumerate(results[:limit], 1):
        lines.append(f"  {i}. {result.title}")
        lines.append(f"     {result.url}")
        if result.snippet:
            snippet = result.snippet[:150]
            if len(result.snippet) > 150:
                snippet += "..."
            lines.append(f"     {snippet}")
        lines.append(f"     Score: {result.relevance_score:.2f}")
        if result.source_interest:
            lines.append(f"     Interest: {result.source_interest}")
        lines.append("")

    return "\n".join(lines)


def format_interest(interest) -> str:
    """Format a single interest for display."""
    status = "enabled" if interest.enabled else "disabled"
    lines = [f"  [{status}] {interest.name} (priority: {interest.priority})"]
    if interest.keywords:
        lines.append(f"    Keywords: {', '.join(interest.keywords)}")
    if interest.topics:
        lines.append(f"    Topics: {', '.join(interest.topics)}")
    if interest.url_patterns:
        lines.append(f"    URL patterns: {', '.join(interest.url_patterns)}")
    return "\n".join(lines)


def format_crawl_stats(stats: dict) -> str:
    """Format crawl statistics."""
    lines = [
        "  Crawl Statistics:",
        f"    Pages crawled:  {stats.get('pages_crawled', 0)}",
        f"    Pages indexed:  {stats.get('pages_indexed', 0)}",
        f"    Pages filtered: {stats.get('pages_filtered', 0)}",
        f"    Errors:         {stats.get('errors', 0)}",
    ]
    return "\n".join(lines)


def format_index_page(page) -> str:
    """Format an indexed page for display."""
    lines = [
        f"  {page.title}",
        f"    URL: {page.url}",
        f"    Score: {page.score:.2f}",
        f"    Words: {page.word_count}",
    ]
    if page.source_interest:
        lines.append(f"    Interest: {page.source_interest}")
    if page.indexed_at:
        lines.append(f"    Indexed: {page.indexed_at}")
    return "\n".join(lines)


def format_schedule_job(job) -> str:
    """Format a scheduled job for display."""
    status = "enabled" if job.enabled else "disabled"
    lines = [
        f"  [{status}] {job.name}",
        f"    URLs: {', '.join(job.seed_urls)}",
        f"    Interval: every {job.interval_hours} hours",
        f"    Runs: {job.run_count}",
    ]
    if job.last_run:
        lines.append(f"    Last run: {job.last_run}")
    if job.status != "pending":
        lines.append(f"    Status: {job.status}")
    if job.error:
        lines.append(f"    Error: {job.error}")
    return "\n".join(lines)


def format_table(headers: list[str], rows: list[list[str]], padding: int = 2) -> str:
    """Format data as a simple text table."""
    if not headers or not rows:
        return ""

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Build format string
    fmt = "  " + "  ".join(f"{{:<{w + padding}}}" for w in col_widths)

    lines = []
    lines.append(fmt.format(*headers))
    lines.append("  " + "-".join("-" * (w + padding) for w in col_widths))
    for row in rows:
        cells = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        lines.append(fmt.format(*cells))

    return "\n".join(lines)


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_file_size(bytes_count: int) -> str:
    """Format a file size in bytes to a human-readable string."""
    if bytes_count < 1024:
        return f"{bytes_count}B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f}KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f}MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.1f}GB"


def format_timestamp(iso_string: str) -> str:
    """Format an ISO timestamp to a human-readable string."""
    if not iso_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_string


def truncate(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def highlight(text: str, terms: list[str]) -> str:
    """Highlight search terms in text (for terminal output)."""
    result = text
    for term in terms:
        if term:
            result = result.replace(term, f"**{term}**")
    return result
