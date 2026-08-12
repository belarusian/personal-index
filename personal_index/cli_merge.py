"""CLI command for content merging."""

from __future__ import annotations

import click

from personal_index.content_merger import ContentMerger, MergeSource


@click.command("merge")
@click.argument("urls", nargs=-1)
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--strategy", "-s", default="concatenate",
              type=click.Choice(["concatenate", "longest", "highest_priority", "unique_paragraphs"]),
              help="Merge strategy")
@click.option("--output-format", "-f", default="text",
              type=click.Choice(["text", "markdown", "json"]),
              help="Output format")
@click.pass_context
def merge(ctx, urls, data_dir, strategy, output_format):
    """Merge content from multiple URLs.

    Combines content from multiple sources using the specified
    merge strategy and outputs in the requested format.

    Examples:
        personal-index merge https://a.com https://b.com
        personal-index merge https://a.com https://b.com --strategy longest
        personal-index merge https://a.com https://b.com --output-format markdown
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    # Load indexed content
    from personal_index.index import SearchIndex
    idx_path = f"{dd}/search_index.json"
    idx = SearchIndex(db_path=idx_path)

    if not urls:
        click.echo("No URLs provided.")
        return

    # Build sources from indexed pages
    sources = []
    for url in urls:
        page = idx.get_page(url)
        if page:
            sources.append(MergeSource(
                url=page.url,
                title=page.title,
                content=page.content or "",
                tags=list(getattr(page, "keywords", []) or []),
                priority=int(page.score),
            ))
        else:
            click.echo(f"Warning: URL not found in index: {url}", err=True)

    if not sources:
        click.echo("No valid URLs found in index.")
        return

    merger = ContentMerger(strategy=strategy)
    result = merger.merge(sources)

    if output_format == "json":
        import json
        click.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format == "markdown":
        md_lines = [
            f"# Merged: {result.title}",
            "",
            f"**Source:** {result.source_count} pages",
            f"**Strategy:** {result.merge_strategy}",
            "",
        ]
        if result.sources:
            md_lines.append("## Sources")
            for src in result.sources:
                md_lines.append(f"- [{src}]({src})")
            md_lines.append("")
        md_lines.append(result.content)
        click.echo("\n".join(md_lines))
    else:  # text
        click.echo(f"Merged: {result.title}")
        click.echo("=" * 40)
        click.echo(f"Source count: {result.source_count}")
        click.echo(f"Strategy: {result.merge_strategy}")
        if result.sources:
            click.echo("\nSources:")
            for src in result.sources:
                click.echo(f"  - {src}")
        click.echo()
        click.echo(result.content[:1000])
        if len(result.content) > 1000:
            click.echo("... (truncated)")
