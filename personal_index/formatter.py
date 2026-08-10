"""Output formatting utilities."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from personal_index.index import IndexedPage, SearchResult
from personal_index.interests import Interest
from personal_index.scheduler import ScheduledJob


def format_search_results(
    results: List[SearchResult], limit: int = 10
) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."

    lines = []
    for i, result in enumerate(results[:limit], 1):
        lines.append(f"{i}. {result.title}")
        lines.append(f"   URL: {result.url}")
        if result.snippet:
            lines.append(f"   {result.snippet}")
        lines.append(f"   Score: {result.relevance_score:.2f}")
        lines.append("")
    return "\n".join(lines)


def format_interest(interest: Interest) -> str:
    """Format an interest for display."""
    status = "enabled" if interest.enabled else "disabled"
    lines = [f"  Name: {interest.name} [{status}]"]
    if interest.keywords:
        lines.append(f"  Keywords: {', '.join(interest.keywords)}")
    if interest.topics:
        lines.append(f"  Topics: {', '.join(interest.topics)}")
    if interest.url_patterns:
        lines.append(
            f"  URL Patterns: {', '.join(interest.url_patterns)}"
        )
    lines.append(f"  Priority: {interest.priority}")
    return "\n".join(lines)


def format_crawl_stats(stats: Dict[str, Any]) -> str:
    """Format crawl statistics."""
    lines = [
        f"  Pages crawled: {stats.get('pages_crawled', 0)}",
        f"  Pages indexed: {stats.get('pages_indexed', 0)}",
        f"  Pages filtered: {stats.get('pages_filtered', 0)}",
        f"  Errors: {stats.get('errors', 0)}",
    ]
    return "\n".join(lines)


def format_index_page(page: IndexedPage) -> str:
    """Format an indexed page for display."""
    lines = [
        f"  Title: {page.title}",
        f"  URL: {page.url}",
        f"  Score: {page.score:.2f}",
        f"  Indexed: {page.indexed_at}",
        f"  Words: {page.word_count}",
    ]
    if page.keywords:
        lines.append(f"  Keywords: {', '.join(page.keywords)}")
    return "\n".join(lines)


def format_schedule_job(job: Union[Dict[str, Any], ScheduledJob]) -> str:
    """Format a scheduled job for display."""
    if isinstance(job, ScheduledJob):
        name = job.name
        interval_hours = job.interval_hours
        run_count = job.run_count
        last_run = job.last_run
        seed_urls = job.seed_urls
    elif isinstance(job, dict):
        name = job.get('name', 'unknown')
        interval_hours = job.get('interval_hours', 0)
        run_count = job.get('run_count', 0)
        last_run = job.get('last_run')
        seed_urls = job.get('seed_urls', [])
    else:
        # Try attribute access as fallback
        name = getattr(job, 'name', 'unknown')
        interval_hours = getattr(job, 'interval_hours', 0)
        run_count = getattr(job, 'run_count', 0)
        last_run = getattr(job, 'last_run', None)
        seed_urls = getattr(job, 'seed_urls', [])

    lines = [
        f"  Name: {name}",
        f"  Interval: {interval_hours} hours",
        f"  Runs: {run_count}",
        f"  Last run: {last_run or 'Never'}",
        f"  Seed URLs: {', '.join(seed_urls)}",
    ]
    return "\n".join(lines)


def format_table(
    headers: List[str], rows: List[List[str]]
) -> str:
    """Format data as a text table."""
    if not headers or not rows:
        return ""

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = " | ".join(
        h.ljust(col_widths[i]) for i, h in enumerate(headers)
    )
    separator = "-+-".join("-" * w for w in col_widths)
    lines = [header_line, separator]
    for row in rows:
        cells = []
        for i in range(len(headers)):
            if i < len(row):
                cells.append(str(row[i]).ljust(col_widths[i]))
            else:
                cells.append("".ljust(col_widths[i]))
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def format_file_size(size: int) -> str:
    """Format file size in bytes to human-readable string."""
    if size < 1024:
        return f"{size}B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}MB"
    return f"{size / (1024 * 1024 * 1024):.1f}GB"


def format_timestamp(timestamp: str | None) -> str:
    """Format a timestamp string for display."""
    if not timestamp:
        return "N/A"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate text to max_length, adding ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def highlight(text: str, terms: List[str]) -> str:
    """Highlight search terms in text with ** markers."""
    if not terms:
        return text
    result = text
    for term in terms:
        if term:
            result = result.replace(term, f"**{term}**")
    return result
