"""Pipeline CLI command for personal-index.

Provides the 'pipeline' command that runs the full
crawl → extract → filter → score → tag → index pipeline.
"""

from __future__ import annotations

import os
import sys
import time

import click

from personal_index.pipeline_runner import PipelineRunner


def progress_callback(stage: str, current: int, total: int) -> None:
    """Click-compatible progress callback."""
    if total > 0:
        pct = int(current / total * 100)
        click.echo(f"\r  [{stage}] {current}/{total} ({pct}%)", nl=False, err=True)
    else:
        click.echo(f"\r  [{stage}] {current} done", nl=False, err=True)


@click.command("pipeline")
@click.argument("urls", nargs=-1)
@click.option("--import-file", "-i", "import_files", multiple=True,
              help="Import local files instead of crawling")
@click.option("--depth", "-d", default=3, type=int, help="Max crawl depth")
@click.option("--max-pages", "-m", default=100, type=int, help="Max pages to crawl")
@click.option("--min-score", default=0.0, type=float, help="Minimum score threshold")
@click.option("--min-content-length", default=100, type=int,
              help="Minimum content length to include")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--no-crawl", is_flag=True, help="Skip crawl stage (use with --import-file)")
@click.option("--no-filter", is_flag=True, help="Skip filter stage")
@click.option("--no-score", is_flag=True, help="Skip score stage")
@click.option("--no-tag", is_flag=True, help="Skip tag stage")
@click.option("--no-index", is_flag=True, help="Skip index stage")
@click.pass_context
def pipeline(ctx, urls, import_files, depth, max_pages, min_score,
             min_content_length, data_dir, no_crawl, no_filter,
             no_score, no_tag, no_index):
    """Run the full content pipeline.

    Processes content through all stages: crawl → extract → filter →
    score → tag → index. Can work with URLs (web crawling) or local
    files (import mode).

    Examples:
        # Crawl and index a website
        personal-index pipeline https://example.com

        # Import local files
        personal-index pipeline --import-file ./article.txt

        # Import directory of files
        personal-index pipeline --import-file ./docs/*.txt

        # Custom settings
        personal-index pipeline https://example.com -d 2 -m 50 --min-score 0.5
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    # Build enabled steps list
    enabled_steps = ["crawl", "extract", "filter", "score", "tag", "index"]
    if no_crawl:
        enabled_steps.remove("crawl")
    if no_filter:
        enabled_steps.remove("filter")
    if no_score:
        enabled_steps.remove("score")
    if no_tag:
        enabled_steps.remove("tag")
    if no_index:
        enabled_steps.remove("index")

    from personal_index.config.pipeline_config import PipelineConfig

    config = PipelineConfig(
        max_depth=depth,
        max_pages=max_pages,
        min_score_threshold=min_score,
        min_content_length=min_content_length,
        enabled_steps=enabled_steps,
    )

    runner = PipelineRunner(
        data_dir=dd,
        pipeline_config=config,
        progress_callback=progress_callback,
    )

    try:
        if import_files:
            click.echo(f"Importing {len(import_files)} file(s)...")
            stats = runner.run_from_files(list(import_files))
        elif urls:
            click.echo(f"Running pipeline on {len(urls)} URL(s)...")
            stats = runner.run(list(urls))
        else:
            click.echo("No URLs or files specified.")
            click.echo("Usage:")
            click.echo("  personal-index pipeline https://example.com")
            click.echo("  personal-index pipeline --import-file ./file.txt")
            sys.exit(1)

        click.echo("")  # newline after progress
        click.echo(f"\nPipeline complete in {stats.elapsed_seconds:.1f}s:")
        click.echo(f"  Crawled:      {stats.pages_crawled}")
        click.echo(f"  Extracted:    {stats.pages_extracted}")
        click.echo(f"  Filtered in:  {stats.pages_filtered_in}")
        click.echo(f"  Filtered out: {stats.pages_filtered_out}")
        click.echo(f"  Scored:       {stats.pages_scored}")
        click.echo(f"  Tagged:       {stats.pages_tagged}")
        click.echo(f"  Tags applied: {stats.tags_applied}")
        click.echo(f"  Indexed:      {stats.pages_indexed}")
        if stats.errors:
            click.echo(f"  Errors:       {len(stats.errors)}")
            for err in stats.errors[:5]:
                click.echo(f"    - {err}")

        # Show final stats
        final_stats = runner.get_stats()
        click.echo("\nIndex stats:")
        click.echo(f"  Total indexed pages: {final_stats['indexed_pages']}")
        click.echo(f"  Total interests:     {final_stats['total_interests']}")
        click.echo(f"  Total tags:          {final_stats['total_tags']}")
        click.echo(f"  Tagged pages:        {final_stats['tagged_pages']}")

    finally:
        runner.close()
