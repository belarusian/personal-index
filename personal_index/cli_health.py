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
def health(
    ctx,
    data_dir,
    min_content_length,
    min_title_length,
    require_tags,
    min_score,
):
    """Check the health of indexed content.

    Analyzes all indexed pages for quality issues including
    missing titles, short content, and bad status codes.

    Examples:
        personal-index health
        personal-index health --require-tags --min-score 5.0
        personal-index health --min-content-length 100
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    # Load indexed content
    from personal_index.index import SearchIndex
    idx_path = f"{dd}/search_index.json"
    idx = SearchIndex(db_path=idx_path)

    # Load tags
    from personal_index.tags import TagStore
    tag_path = f"{dd}/tags.json"
    tag_store = TagStore(store_path=tag_path)

    pages = idx.list_pages()
    if not pages:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    # Build items for health check
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

    # Configure and run health check
    config = ContentHealthCheck(
        min_content_length=min_content_length,
        min_title_length=min_title_length,
        require_tags=require_tags,
        require_score=min_score > 0,
        min_score=min_score,
    )
    checker = ContentHealthChecker(config=config)
    report = checker.check_all(items)

    # Print report
    click.echo(report.summary())
    click.echo()

    # Print issues
    if report.total_issues > 0:
        click.echo(f"Issues Found ({report.total_issues}):")
        click.echo("-" * 40)
        for result in report.results:
            if result.issues:
                click.echo(f"\n  {result.url}")
                for issue in result.issues:
                    severity_icon = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🔵",
                    }.get(issue.severity.value, "⚪")
                    click.echo(f"    {severity_icon} [{issue.severity.value}] {issue.message}")
                    if issue.suggestion:
                        click.echo(f"       → {issue.suggestion}")
    else:
        click.echo("✓ All content is healthy!")
