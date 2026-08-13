"""CLI command for content health checks."""

from __future__ import annotations

import click

from personal_index.content_health import (
    ContentHealthCheck,
    ContentHealthChecker,
)


@click.command("health")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--min-content-length", type=int, default=50, help="Minimum content length")
@click.option("--min-title-length", type=int, default=3, help="Minimum title length")
@click.option("--require-tags", is_flag=True, help="Require tags on all items")
@click.option("--min-score", type=float, default=0.0, help="Minimum score threshold")
@click.pass_context
def health(ctx, data_dir, min_content_length, min_title_length, require_tags, min_score):
    """Check the health of indexed content."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx, tag_store = _load_stores(dd)

    pages = idx.list_pages()
    if not pages:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    items = _build_health_items(pages, tag_store)
    config = _build_config(min_content_length, min_title_length, require_tags, min_score)
    checker = ContentHealthChecker(config=config)
    report = checker.check_all(items)

    _print_report(report)


def _load_stores(data_dir: str):
    from personal_index.index import SearchIndex
    from personal_index.tags import TagStore
    idx = SearchIndex(db_path=f"{data_dir}/search_index.json")
    tag_store = TagStore(store_path=f"{data_dir}/tags.json")
    return idx, tag_store


def _build_health_items(pages, tag_store):
    items = []
    for page in pages:
        page_tags = list(tag_store.get_tags_for_url(page.url))
        items.append({
            "url": page.url,
            "title": page.title,
            "content": page.content or "",
            "tags": page_tags,
            "score": page.score,
            "status_code": getattr(page, "status_code", 200),
        })
    return items


def _build_config(min_content_length, min_title_length, require_tags, min_score):
    return ContentHealthCheck(
        min_content_length=min_content_length,
        min_title_length=min_title_length,
        require_tags=require_tags,
        require_score=min_score > 0,
        min_score=min_score,
    )


def _print_report(report):
    click.echo(report.summary())
    click.echo()
    if report.total_issues > 0:
        _print_issues(report)
    else:
        click.echo("✓ All content is healthy!")


def _print_issues(report):
    click.echo(f"Issues Found ({report.total_issues}):")
    click.echo("-" * 40)
    for result in report.results:
        if result.issues:
            click.echo(f"\n  {result.url}")
            for issue in result.issues:
                icon = _severity_icon(issue.severity.value)
                click.echo(f"    {icon} [{issue.severity.value}] {issue.message}")
                if issue.suggestion:
                    click.echo(f"       → {issue.suggestion}")


def _severity_icon(severity: str) -> str:
    return {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
    }.get(severity, "⚪")
