"""CLI pipeline command for personal-index."""

from __future__ import annotations

import logging
import click

from personal_index.config.pipeline_config import load_pipeline_config
from personal_index.pipeline_runner import PipelineRunner


@click.command()
@click.argument("urls", nargs=-1, required=True)
@click.option("-d", "--depth", default=3, type=int, help="Crawl depth")
@click.option("--config", default="config.yaml", help="Config file path")
@click.option("--data-dir", default=".personal_index", help="Data directory")
@click.option("--dry-run", is_flag=True, help="Show what would be done without running")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option("-o", "--output", default=None, help="Save pipeline stats to file")
def pipeline(urls, depth, config, data_dir, dry_run, verbose, output):
    """Run the full pipeline: crawl → extract → filter → score → tag → index.

    URLs are the seed URLs to start crawling from.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    pipeline_cfg = load_pipeline_config(config)

    if dry_run:
        click.echo("Dry run mode - pipeline configuration:")
        click.echo(f"  Config: {config}")
        click.echo(f"  Data dir: {data_dir}")
        click.echo(f"  Seed URLs: {', '.join(urls)}")
        click.echo(f"  Max depth: {depth}")
        click.echo(f"  Pipeline enabled: {pipeline_cfg.enabled}")
        click.echo(f"  Steps: {pipeline_cfg.get_enabled_steps()}")
        click.echo(f"  Min score threshold: {pipeline_cfg.min_score_threshold}")
        click.echo(f"  Min content length: {pipeline_cfg.min_content_length}")
        return

    click.echo(f"Running pipeline on {len(urls)} seed URL(s)...")
    click.echo(f"  URLs: {', '.join(urls)}")
    click.echo(f"  Depth: {depth}")
    click.echo()

    runner = PipelineRunner(
        config=pipeline_cfg,
        data_dir=data_dir,
    )
    stats = runner.run(list(urls), max_depth=depth)

    click.echo()
    click.echo(stats.summary())

    if output:
        with open(output, "w") as f:
            f.write(stats.summary())
        click.echo(f"Stats saved to {output}")

    if stats.errors:
        click.echo("\nErrors:")
        for err in stats.errors:
            click.echo(f"  - {err}")
