"""CLI pipeline command for personal-index."""

from __future__ import annotations

import logging
import sys
import time

import click

from personal_index.config.pipeline_config import PipelineStepConfig, load_pipeline_config
from personal_index.pipeline_runner import PipelineRunner


@click.command()
@click.argument("urls", nargs=-1, required=False)
@click.option("-d", "--depth", default=3, type=int, help="Crawl depth")
@click.option("--config", default="config.yaml", help="Config file path")
@click.option("--data-dir", default=".personal_index", help="Data directory")
@click.option("--dry-run", is_flag=True, help="Show what would be done without running")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.option("-o", "--output", default=None, help="Save pipeline stats to file")
@click.option("-q", "--quiet", is_flag=True, help="Minimal output, only show errors")
@click.option("--no-crawl", is_flag=True, help="Skip crawling, only process existing data")
@click.option("--step", type=click.Choice(["crawl", "extract", "filter", "score", "tag", "index"]),
              multiple=True, help="Run only specific pipeline steps")
@click.option("--min-score", type=float, default=None, help="Override minimum score threshold")
@click.option("--min-length", type=int, default=None, help="Override minimum content length")
def pipeline(urls, depth, config, data_dir, dry_run, verbose, output, quiet, no_crawl, step, min_score, min_length):
    """Run the full pipeline: crawl → extract → filter → score → tag → index.

    URLs are the seed URLs to start crawling from. If no URLs are provided,
    the pipeline processes existing indexed content.

    Examples:
        personal-index pipeline https://example.com
        personal-index pipeline https://example.com -d 2
        personal-index pipeline --no-crawl  # re-process existing data
        personal-index pipeline https://example.com --step filter --step score
        personal-index pipeline https://example.com --min-score 0.5
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    pipeline_cfg = load_pipeline_config(config)

    # Apply overrides
    if min_score is not None:
        pipeline_cfg.min_score_threshold = min_score
    if min_length is not None:
        pipeline_cfg.min_content_length = min_length

    # Override steps if --step is provided
    if step:
        all_steps = ["crawl", "extract", "filter", "score", "tag", "index"]
        pipeline_cfg.steps = []
        for s in all_steps:
            enabled = s in step
            pipeline_cfg.steps.append(PipelineStepConfig(name=s, enabled=enabled))

    if no_crawl:
        all_steps = ["crawl", "extract", "filter", "score", "tag", "index"]
        pipeline_cfg.steps = []
        for s in all_steps:
            pipeline_cfg.steps.append(PipelineStepConfig(name=s, enabled=(s != "crawl")))

    if dry_run:
        click.echo("Dry run mode - pipeline configuration:")
        click.echo(f"  Config: {config}")
        click.echo(f"  Data dir: {data_dir}")
        if urls:
            click.echo(f"  Seed URLs: {', '.join(urls)}")
        else:
            click.echo("  Seed URLs: (none, using existing data)")
        click.echo(f"  Max depth: {depth}")
        click.echo(f"  Pipeline enabled: {pipeline_cfg.enabled}")
        click.echo(f"  Steps: {pipeline_cfg.get_enabled_steps()}")
        click.echo(f"  Min score threshold: {pipeline_cfg.min_score_threshold}")
        click.echo(f"  Min content length: {pipeline_cfg.min_content_length}")
        return

    if not quiet:
        click.echo(f"Running pipeline on {len(urls)} seed URL(s)...")
        if urls:
            click.echo(f"  URLs: {', '.join(urls)}")
        click.echo(f"  Depth: {depth}")
        click.echo(f"  Data dir: {data_dir}")
        click.echo()

    runner = PipelineRunner(
        config=pipeline_cfg,
        data_dir=data_dir,
    )

    if not quiet:
        click.echo("Pipeline steps:")
        steps = ["crawl", "extract", "filter", "score", "tag", "index"]
        for s in steps:
            enabled = pipeline_cfg.is_step_enabled(s)
            status = "✓" if enabled else "○"
            click.echo(f"  [{status}] {s}")
        click.echo()

    seed_urls = list(urls) if urls else []

    start_time = time.time()
    stats = runner.run(seed_urls, max_depth=depth)
    elapsed = time.time() - start_time

    if not quiet:
        click.echo()
        click.echo(stats.summary())

        if stats.pages_indexed > 0:
            click.echo()
            click.echo("Next steps:")
            click.echo("  Search: personal-index search 'your query'")
            click.echo("  Export: personal-index export --format markdown")
            click.echo("  Status: personal-index status")

    if output:
        with open(output, "w") as f:
            f.write(stats.summary())
        click.echo(f"\nStats saved to {output}")

    if stats.errors:
        click.echo("\nErrors encountered:")
        for err in stats.errors:
            click.echo(f"  - {err}")
        sys.exit(1)
