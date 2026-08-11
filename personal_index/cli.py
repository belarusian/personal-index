"""CLI interface for personal-index."""

from __future__ import annotations

import json
import os
import sys

import click
import yaml

from personal_index.app import PersonalIndexApp
from personal_index.models import Interest


def get_app(ctx: click.Context | None = None) -> PersonalIndexApp:
    """Get the application instance from click context or create one."""
    if ctx and ctx.obj:
        return ctx.obj.get("app")
    config_path = os.environ.get("PERSONAL_INDEX_CONFIG", "config.yaml")
    data_dir = os.environ.get("PERSONAL_INDEX_DATA_DIR", ".personal_index")
    return PersonalIndexApp(config_path=config_path, data_dir=data_dir)


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def main(ctx: click.Context):
    """personal-index - Track and index content matching your interests.

    A personal web search engine that scans, filters, and indexes
    the web based on your interests.
    """
    app = PersonalIndexApp()
    ctx.ensure_object(dict)
    ctx.obj["app"] = app


# ─── Init ────────────────────────────────────────────────────────────────

@main.command()
@click.option("--data-dir", default=".personal_index", help="Data directory")
@click.option("--config", default="config.yaml", help="Config file path")
@click.pass_context
def init(ctx: click.Context, data_dir: str, config: str):
    """Initialize a new personal-index project."""
    app = PersonalIndexApp(config_path=config, data_dir=data_dir)
    app.initialize()

    # Create default config if it doesn't exist
    if not os.path.exists(config):
        default_config = {
            "data_dir": data_dir,
            "crawler": {
                "max_depth": 5,
                "politeness_delay": 1.0,
                "rate_limit": 10,
                "respect_robots_txt": True,
                "timeout": 30,
            },
            "scheduler": {
                "enabled": False,
                "interval_hours": 24,
            },
            "index": {
                "enable_stemming": True,
                "index_path": data_dir,
            },
            "interests": [],
        }
        with open(config, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        click.echo(f"Created config file: {config}")

    os.makedirs(data_dir, exist_ok=True)
    click.echo(f"Initialized personal-index in {data_dir}")
    click.echo("Run 'personal-index interests add' to start tracking topics.")


# ─── Interests ───────────────────────────────────────────────────────────

@main.group()
def interests():
    """Manage tracked interests."""
    pass


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keyword", multiple=True, help="Keywords to track")
@click.option("-u", "--url-pattern", multiple=True, help="URL patterns to match")
@click.option("-p", "--priority", default=5, type=int, help="Priority (1-10)")
@click.pass_context
def add_interest(ctx: click.Context, name: str, keyword: tuple[str, ...],
                 url_pattern: tuple[str, ...], priority: int):
    """Add a new interest to track."""
    app = get_app(ctx)
    app.add_interest(
        name=name,
        keywords=list(keyword),
        url_patterns=list(url_pattern),
        priority=priority,
    )
    click.echo(f"Added interest: {name}")


@interests.command("list")
@click.pass_context
def list_interests(ctx: click.Context):
    """List all tracked interests."""
    app = get_app(ctx)
    all_interests = app.interest_store.list_all()
    if not all_interests:
        click.echo("No interests configured.")
        return
    for interest in all_interests:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  {interest.name} [{status}] priority={interest.priority}")
        if interest.keywords:
            click.echo(f"    keywords: {', '.join(interest.keywords)}")
        if interest.url_patterns:
            click.echo(f"    patterns: {', '.join(interest.url_patterns)}")


@interests.command("remove")
@click.argument("name")
@click.pass_context
def remove_interest(ctx: click.Context, name: str):
    """Remove an interest by name."""
    app = get_app(ctx)
    if app.interest_store.remove(name):
        click.echo(f"Removed interest: {name}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        raise SystemExit(1)


@interests.command("toggle")
@click.argument("name")
@click.pass_context
def toggle_interest(ctx: click.Context, name: str):
    """Toggle an interest on/off."""
    app = get_app(ctx)
    interest = app.interest_store.toggle(name)
    if interest:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"Interest '{name}' is now {status}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        raise SystemExit(1)


# ─── Search ──────────────────────────────────────────────────────────────

@main.command()
@click.argument("query")
@click.option("-l", "--limit", default=20, type=int, help="Max results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def search(ctx: click.Context, query: str, limit: int, as_json: bool):
    """Search indexed content."""
    app = get_app(ctx)
    results = app.search(query, limit=limit)
    if as_json:
        click.echo(json.dumps(results, indent=2, default=str))
    else:
        if not results:
            click.echo("No results found.")
            return
        click.echo(f"Found {len(results)} results for '{query}':\n")
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            score = r.get("score", 0)
            click.echo(f"  {i}. {title}")
            if url:
                click.echo(f"     {url}")
            click.echo(f"     score: {score:.2f}")
            click.echo()


# ─── Process ─────────────────────────────────────────────────────────────

@main.command()
@click.option("--url", required=True, help="Source URL")
@click.option("--title", default="", help="Page title")
@click.option("--content", default="", help="Raw content text")
@click.option("--file", "content_file", type=click.Path(exists=True),
              help="Read content from file")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def process(ctx: click.Context, url: str, title: str, content: str,
            content_file: str | None, as_json: bool):
    """Process and index content."""
    app = get_app(ctx)
    if content_file:
        with open(content_file) as f:
            content = f.read()
    result = app.process_content(url, content, title)
    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        click.echo(f"Processed: {url}")
        click.echo(f"  Title: {result.get('title', 'N/A')}")
        click.echo(f"  Score: {result.get('score', 0):.2f}")
        click.echo(f"  Tags: {', '.join(result.get('tags', []))}")
        click.echo(f"  Indexed: {'Yes' if result.get('passes_filter') else 'No'}")


# ─── Stats ───────────────────────────────────────────────────────────────

@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def stats(ctx: click.Context, as_json: bool):
    """Show index statistics."""
    app = get_app(ctx)
    s = app.get_stats()
    if as_json:
        click.echo(json.dumps(s, indent=2))
    else:
        click.echo("Personal Index Statistics")
        click.echo("=" * 30)
        click.echo(f"  Indexed items:    {s['indexed_items']}")
        click.echo(f"  Interests:        {s['interests']}")
        click.echo(f"  Scheduled jobs:   {s['scheduled_jobs']}")
        click.echo(f"  Pipeline steps:   {s['pipeline_steps']}")
        click.echo(f"  Enabled steps:    {', '.join(s['enabled_steps'])}")
        click.echo(f"  Data directory:   {s['data_dir']}")


# ─── Schedule ────────────────────────────────────────────────────────────

@main.group()
def schedule():
    """Manage scheduled jobs."""
    pass


@schedule.command("add")
@click.option("-n", "--name", required=True, help="Job name")
@click.option("-u", "--url", multiple=True, help="Seed URLs")
@click.option("-i", "--interval", default=24, type=int, help="Interval in hours")
@click.pass_context
def add_schedule(ctx: click.Context, name: str, url: tuple[str, ...], interval: int):
    """Add a scheduled crawl job."""
    app = get_app(ctx)
    from personal_index.scheduler import JobConfig
    config = JobConfig(name=name, seed_urls=list(url), interval_hours=interval)
    app.scheduler.add_job(config)
    click.echo(f"Added scheduled job: {name} (every {interval}h)")


@schedule.command("list")
@click.pass_context
def list_schedules(ctx: click.Context):
    """List scheduled jobs."""
    app = get_app(ctx)
    jobs = app.scheduler.list_jobs()
    if not jobs:
        click.echo("No scheduled jobs.")
        return
    for job in jobs:
        urls = ", ".join(job.config.seed_urls) if job.config.seed_urls else "none"
        click.echo(f"  {job.name}: {urls} (every {job.config.interval_hours}h)")


@schedule.command("remove")
@click.argument("name")
@click.pass_context
def remove_schedule(ctx: click.Context, name: str):
    """Remove a scheduled job."""
    app = get_app(ctx)
    if app.scheduler.remove_job(name):
        click.echo(f"Removed scheduled job: {name}")
    else:
        click.echo(f"Job not found: {name}", err=True)
        raise SystemExit(1)


# ─── Config ──────────────────────────────────────────────────────────────

@main.group()
def config():
    """Manage configuration."""
    pass


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context):
    """Show current configuration."""
    app = get_app(ctx)
    cfg = app.config
    click.echo(f"Config file: {app.config_path}")
    click.echo(f"Data dir: {cfg.data_dir}")
    click.echo("\nCrawler:")
    click.echo(f"  Max depth: {cfg.crawl.max_depth}")
    click.echo(f"  Politeness delay: {cfg.crawl.politeness_delay}s")
    click.echo(f"  Rate limit: {cfg.crawl.rate_limit}")
    click.echo(f"  Timeout: {cfg.crawl.timeout}s")
    click.echo(f"  Respect robots.txt: {cfg.crawl.respect_robots_txt}")
    click.echo("\nSchedule:")
    click.echo(f"  Enabled: {cfg.scheduler.enabled}")
    click.echo(f"  Interval: {cfg.scheduler.interval_hours}h")


@config.command("set-crawler")
@click.option("--max-depth", type=int, help="Max crawl depth")
@click.option("--delay", type=float, help="Politeness delay")
@click.option("--concurrent", type=int, help="Max concurrent requests")
@click.option("--timeout", type=int, help="Request timeout")
@click.pass_context
def config_set_crawler(ctx: click.Context, max_depth: int | None, delay: float | None,
                       concurrent: int | None, timeout: int | None):
    """Set crawler configuration."""
    from personal_index.config.loader import save_config
    app = get_app(ctx)
    cfg = app.config
    if max_depth is not None:
        cfg.crawl.max_depth = max_depth
    if delay is not None:
        cfg.crawl.politeness_delay = delay
    if concurrent is not None:
        cfg.crawl.rate_limit = concurrent
    if timeout is not None:
        cfg.crawl.timeout = timeout
    save_config(cfg, app.config_path)
    click.echo("Crawler config updated.")


@config.command("set-schedule")
@click.option("--interval", type=int, help="Interval in hours")
@click.option("--enable", is_flag=True, help="Enable scheduling")
@click.option("--disable", is_flag=True, help="Disable scheduling")
@click.pass_context
def config_set_schedule(ctx: click.Context, interval: int | None, enable: bool, disable: bool):
    """Set schedule configuration."""
    from personal_index.config.loader import save_config
    app = get_app(ctx)
    cfg = app.config
    if interval is not None:
        cfg.scheduler.interval_hours = interval
    if enable:
        cfg.scheduler.enabled = True
    if disable:
        cfg.scheduler.enabled = False
    save_config(cfg, app.config_path)
    click.echo("Schedule config updated.")


# ─── Health ──────────────────────────────────────────────────────────────

@main.command()
@click.pass_context
def health(ctx: click.Context):
    """Check system health."""
    app = get_app(ctx)
    app.initialize()
    issues = []

    # Check data directory
    if not os.path.isdir(app.data_dir):
        issues.append(f"Data directory missing: {app.data_dir}")

    # Check config
    try:
        _ = app.config
    except Exception as e:
        issues.append(f"Config error: {e}")

    # Check pipeline
    if app.pipeline.step_count == 0:
        issues.append("Pipeline has no steps")

    if issues:
        click.echo("Health check: FAILED")
        for issue in issues:
            click.echo(f"  ✗ {issue}")
        raise SystemExit(1)
    else:
        click.echo("Health check: OK")
        click.echo(f"  ✓ Data directory: {app.data_dir}")
        click.echo(f"  ✓ Config loaded")
        click.echo(f"  ✓ Pipeline: {app.pipeline.step_count} steps")
        click.echo(f"  ✓ Search index: {len(app.search_index._items)} items")


# ─── Dashboard ───────────────────────────────────────────────────────────

@main.command()
@click.option("--output", "-o", default="docs_dashboard.html", help="Output file")
@click.pass_context
def dashboard(ctx: click.Context, output: str):
    """Generate a dashboard HTML file."""
    app = get_app(ctx)
    app.initialize()
    from personal_index.docs_generator import generate_dashboard
    stats = app.get_stats()
    interests = app.interest_store.list_all()
    results = app.search("", limit=50)
    html = generate_dashboard(
        title="Personal Index Dashboard",
        stats=stats,
        interests=interests,
        recent_results=results[:20],
    )
    with open(output, "w") as f:
        f.write(html)
    click.echo(f"Dashboard written to {output}")


if __name__ == "__main__":
    main()
