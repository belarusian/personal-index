"""CLI pipeline command for personal-index.

Provides the 'personal-index pipeline' command that runs the full
crawl → extract → filter → score → tag → index pipeline.
"""

from __future__ import annotations

import os
import sys
import time

import click

from personal_index.models import CrawledPage
from personal_index.pipeline import Pipeline, PipelineConfig


@click.command("pipeline")
@click.argument("urls", nargs=-1, required=False)
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--depth", "-d", default=3, type=int, help="Max crawl depth")
@click.option("--max-pages", "-m", default=100, type=int, help="Maximum pages to crawl")
@click.option("--timeout", "-t", default=30, type=int, help="Request timeout in seconds")
@click.option("--delay", default=1.0, type=float, help="Delay between requests")
@click.option("--min-score", default=0.0, type=float, help="Minimum relevance score threshold")
@click.option("--min-content-length", default=100, type=int, help="Minimum content length")
@click.option("--steps", default=None, help="Comma-separated list of steps to run")
@click.option("--skip-crawl", is_flag=True, help="Skip crawl step (use with --import)")
@click.option("--import-file", "import_files", multiple=True, help="Import local files instead of crawling")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def pipeline(ctx, urls, data_dir, depth, max_pages, timeout, delay,
             min_score, min_content_length, steps, skip_crawl, import_files, dry_run, verbose):
    """Run the full pipeline: crawl → extract → filter → score → tag → index.

    Processes URLs through the complete pipeline, optionally importing local files.

    Examples:
        personal-index pipeline https://example.com
        personal-index pipeline https://example.com https://blog.example.com
        personal-index pipeline --import-file ./docs/readme.md --import-file ./notes.txt
        personal-index pipeline https://example.com --steps extract,filter,score,index
        personal-index pipeline https://example.com --min-score 0.5
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    # Build pipeline config
    enabled_steps = None
    if steps:
        enabled_steps = [s.strip() for s in steps.split(",")]
    elif skip_crawl:
        enabled_steps = ["extract", "filter", "score", "tag", "index"]

    config = PipelineConfig(
        max_depth=depth,
        max_pages=max_pages,
        timeout=timeout,
        politeness_delay=delay,
        min_score_threshold=min_score,
        min_content_length=min_content_length,
    )
    if enabled_steps:
        config.enabled_steps = enabled_steps

    # Handle dry-run mode
    if dry_run:
        click.echo("Dry run mode - no changes will be made")
        click.echo(f"Would process {len(urls) if urls else 0} URL(s) and {len(import_files)} file(s)")
        click.echo(f"Steps: {', '.join(config.enabled_steps)}")
        click.echo(f"Data dir: {dd}")
        click.echo(f"Min score: {min_score}")
        click.echo(f"Min content length: {min_content_length}")
        return

    # Initialize pipeline
    pipe = Pipeline(data_dir=dd, config=config)

    # Load existing interests from data directory
    interest_count = len(pipe.interest_store.list_all())
    if interest_count > 0:
        click.echo(f"Loaded {interest_count} interest(s) from {dd}")
    else:
        click.echo("No interests configured. Adding content without interest filtering.")
        click.echo("Add interests with: personal-index interests add <name> -k <keyword>")

    click.echo(f"Running pipeline in {dd}")
    click.echo(f"Steps: {', '.join(config.enabled_steps)}")

    # Progress callback
    last_step = ""
    last_pct = 0

    def progress_callback(step: str, current: int, total: int):
        nonlocal last_step, last_pct
        pct = int(current / max(total, 1) * 100)
        if step != last_step or pct - last_pct >= 10:
            click.echo(f"  [{step}] {current}/{total} ({pct}%)")
            last_step = step
            last_pct = pct

    start_time = time.time()

    if import_files:
        # Import local files
        click.echo(f"Importing {len(import_files)} local file(s)...")
        imported = 0
        filtered = 0
        errors = 0
        for filepath in import_files:
            if not os.path.exists(filepath):
                click.echo(f"  Warning: {filepath} not found, skipping", err=True)
                errors += 1
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                page = CrawledPage(
                    url=f"file://{os.path.abspath(filepath)}",
                    title=os.path.basename(filepath),
                    content=content,
                    status_code=200,
                )
                if pipe.add_page_directly(page):
                    imported += 1
                    click.echo(f"  Imported: {filepath}")
                else:
                    filtered += 1
                    click.echo(f"  Filtered out: {filepath}")
            except Exception as e:
                click.echo(f"  Error importing {filepath}: {e}", err=True)
                errors += 1
        click.echo(f"Imported {imported}/{len(import_files)} files "
                   f"({filtered} filtered, {errors} errors)")
    elif urls:
        # Run crawl pipeline
        click.echo(f"Crawling {len(urls)} seed URL(s)...")
        stats = pipe.run(list(urls), callback=progress_callback)
        click.echo(f"\nPipeline complete in {stats.elapsed_seconds:.1f}s:")
        click.echo(f"  Crawled:      {stats.pages_crawled}")
        click.echo(f"  Extracted:    {stats.pages_extracted}")
        click.echo(f"  Passed filter:{stats.pages_passed_filter}")
        click.echo(f"  Scored:       {stats.pages_scored}")
        click.echo(f"  Tagged:       {stats.pages_tagged}")
        click.echo(f"  Indexed:      {stats.pages_indexed}")
        if stats.errors:
            click.echo(f"  Errors:       {len(stats.errors)}")
            for err in stats.errors[:5]:
                click.echo(f"    - {err}")
    else:
        click.echo("No URLs or files specified.")
        click.echo("Usage:")
        click.echo("  personal-index pipeline https://example.com")
        click.echo("  personal-index pipeline --import-file ./file.txt")
        sys.exit(1)

    # Show final stats
    final_stats = pipe.get_stats()
    click.echo("\nIndex stats:")
    click.echo(f"  Total indexed pages: {final_stats['indexed_pages']}")
    click.echo(f"  Total interests:     {final_stats['total_interests']}")
    click.echo(f"  Total tags:          {final_stats['total_tags']}")
    click.echo(f"  Tagged pages:        {final_stats['tagged_pages']}")
