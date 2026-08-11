"""Extract CLI command for personal-index.

Provides the 'extract' command that extracts content from URLs
or local files without running the full pipeline.
"""

from __future__ import annotations

import sys

import click

from personal_index.content_extractor import ContentExtractor


@click.command("extract")
@click.argument("sources", nargs=-1)
@click.option("--format", "-f", "output_format", default="text",
              type=click.Choice(["text", "html", "markdown"]),
              help="Output format")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def extract(ctx, sources, output_format, output, data_dir):
    """Extract content from URLs or local files.

    Downloads and extracts readable content from web pages or reads
    local files, outputting in the specified format.

    Examples:
        personal-index extract https://example.com
        personal-index extract ./article.html --format markdown
        personal-index extract https://example.com -o output.txt
    """
    if not sources:
        click.echo("Error: No sources provided.", err=True)
        click.echo("Usage: personal-index extract <url|file> [url|file ...]", err=True)
        sys.exit(1)

    extractor = ContentExtractor()

    results = []
    for source in sources:
        try:
            if source.startswith(("http://", "https://")):
                result = extractor.extract_from_url(source)
            else:
                result = extractor.extract_from_file(source)
            results.append(result)
            click.echo(f"Extracted from {source}: {len(result.content or '')} chars")
            click.echo(f"  Title: {result.title}")
        except (OSError, ValueError) as e:
            click.echo(f"Error extracting {source}: {e}", err=True)

    if output and results:
        combined = "\n\n---\n\n".join(
            r.content or "" for r in results
        )
        with open(output, "w") as f:
            f.write(combined)
        click.echo(f"\nSaved to {output}")
