"""CLI interface for personal-index."""

from __future__ import annotations

import json
import os
import sys

import click
import yaml

from personal_index.cli_pipeline import pipeline as pipeline_cmd
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest, SearchResult
from personal_index.scheduler import Scheduler
from personal_index.tags import TagStore


def get_search_index(data_dir: str | None = None) -> SearchIndex:
    """Get a SearchIndex with persistent storage in the data directory."""
    if data_dir is None:
        data_dir = ".personal_index"
    index_path = os.path.join(data_dir, "search_index.json")
    return SearchIndex(db_path=index_path)


def get_interest_store(data_dir: str | None = None) -> InterestStore:
    """Get an InterestStore with default path."""
    if data_dir is None:
        data_dir = ".personal_index"
    os.makedirs(data_dir, exist_ok=True)
    return InterestStore(store_path=os.path.join(data_dir, "interests.json"))


def get_tag_store(data_dir: str | None = None) -> TagStore:
    """Get a TagStore with default path."""
    if data_dir is None:
        data_dir = ".personal_index"
    os.makedirs(data_dir, exist_ok=True)
    return TagStore(store_path=os.path.join(data_dir, "tags.json"))


@click.group()
@click.version_option(version="0.1.0")
@click.option("--data-dir", default=None, help="Data directory", envvar="PERSONAL_INDEX_DATA_DIR")
@click.pass_context
def main(ctx, data_dir):
    """personal-index - Track and index content matching your interests.

    A personal web search engine that crawls, filters, scores, tags,
    and indexes content based on your defined interests.
    """
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir or ".personal_index"


# Register pipeline command
main.add_command(pipeline_cmd, "pipeline")


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--config", default="config.yaml", help="Config file path")
@click.pass_context
def init(ctx, data_dir, config):
    """Initialize a new personal-index project.

    Creates a data directory and default configuration file with sample interests.
    """
    if data_dir is None:
        data_dir = ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(data_dir, exist_ok=True)

    # Create default config if it doesn't exist
    if not os.path.exists(config):
        default_config = {
            "data_dir": data_dir,
            "crawler": {
                "max_depth": 3,
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
            "pipeline": {
                "enabled": True,
                "min_score_threshold": 0.0,
                "min_content_length": 100,
            },
            "interests": [
                {
                    "name": "technology",
                    "keywords": ["python", "javascript", "programming", "software", "development"],
                    "priority": 8,
                },
                {
                    "name": "science",
                    "keywords": ["research", "study", "experiment", "data", "analysis"],
                    "priority": 7,
                },
            ],
        }
        with open(config, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        click.echo(f"Created config file: {config}")

    # Initialize interest store with sample interests if empty
    store = get_interest_store(data_dir)
    if not store.list_all():
        sample_interests = [
            Interest(
                name="technology",
                keywords=["python", "javascript", "programming", "software", "development"],
                priority=8,
            ),
            Interest(
                name="science",
                keywords=["research", "study", "experiment", "data", "analysis"],
                priority=7,
            ),
        ]
        for interest in sample_interests:
            store.add(interest)
        click.echo("Added sample interests: technology, science")

    click.echo(f"Initialized personal-index in {data_dir}")
    click.echo("")
    click.echo("Next steps:")
    click.echo("  1. Add interests: personal-index interests add -n python -k python -k programming")
    click.echo("  2. Import files:  personal-index import ./my_files/")
    click.echo("  3. Search:        personal-index search python")
    click.echo("  4. Run pipeline:  personal-index pipeline https://example.com")
    click.echo("  5. Check status:  personal-index status")


@main.group()
def interests():
    """Manage tracked interests.

    Interests define what content personal-index should track and prioritize.
    Each interest has keywords and URL patterns that determine matching.
    """


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keyword", multiple=True, help="Keywords to track")
@click.option("-u", "--url-pattern", multiple=True, help="URL patterns to match")
@click.option("-p", "--priority", default=5, type=int, help="Priority (1-10)")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_add(ctx, name, keyword, url_pattern, priority, data_dir):
    """Add a new interest to track."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    interest = Interest(
        name=name,
        keywords=list(keyword),
        url_patterns=list(url_pattern),
        priority=max(1, min(10, priority)),
    )
    store.add(interest)
    click.echo(f"Added interest: {name}")
    if keyword:
        click.echo(f"  Keywords: {', '.join(keyword)}")
    if url_pattern:
        click.echo(f"  URL patterns: {', '.join(url_pattern)}")
    click.echo(f"  Priority: {interest.priority}")


@interests.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_list(ctx, data_dir):
    """List all tracked interests."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    all_interests = store.list_all()
    if not all_interests:
        click.echo("No interests configured. Add one with 'personal-index interests add'")
        return
    for interest in all_interests:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  [{status}] {interest.name} (priority: {interest.priority})")
        if interest.keywords:
            click.echo(f"    Keywords: {', '.join(interest.keywords)}")
        if interest.url_patterns:
            click.echo(f"    URL patterns: {', '.join(interest.url_patterns)}")


@interests.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_remove(ctx, name, data_dir):
    """Remove an interest by name."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    if store.remove(name):
        click.echo(f"Removed interest: {name}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        sys.exit(1)


@interests.command("enable")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_enable(ctx, name, data_dir):
    """Enable an interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    result = store.toggle(name)
    if result is None:
        click.echo(f"Interest not found: {name}", err=True)
        sys.exit(1)
    if result.enabled:
        click.echo(f"Enabled interest: {name}")
    else:
        click.echo(f"Disabled interest: {name}")


@interests.command("disable")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_disable(ctx, name, data_dir):
    """Disable an interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    interest = store.get(name)
    if interest is None:
        click.echo(f"Interest not found: {name}", err=True)
        sys.exit(1)
    interest.enabled = False
    store._save()
    click.echo(f"Disabled interest: {name}")


@interests.command("priority")
@click.argument("name")
@click.argument("level", type=int)
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_priority(ctx, name, level, data_dir):
    """Set priority for an interest (1-10)."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    result = store.update_priority(name, level)
    if result is None:
        click.echo(f"Interest not found: {name}", err=True)
        sys.exit(1)
    click.echo(f"Set priority for '{name}' to {result.priority}")


@main.command()
@click.argument("query")
@click.option("-n", "--limit", default=20, type=int, help="Max results")
@click.option("--snippet", is_flag=True, help="Show content snippets")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def search(ctx, query, limit, snippet, data_dir):
    """Search indexed content.

    Searches across all indexed pages for the given query term.
    Results are ranked by relevance score.

    Examples:
        personal-index search python
        personal-index search "machine learning" -n 10
        personal-index search javascript --snippet
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    results = idx.search(query, limit=limit)

    if not results:
        click.echo(f"No results found for: {query}")
        return

    click.echo(f"Found {len(results)} result(s) for '{query}':")
    click.echo("")

    for i, result in enumerate(results, 1):
        # Handle both SearchResult objects and dicts
        if isinstance(result, SearchResult):
            title = result.title or result.url
            url = result.url
            score = result.relevance_score
            snippet_text = result.snippet
        else:
            title = result.get("title", result.get("url", "Unknown"))
            url = result.get("url", "")
            score = result.get("score", 0)
            snippet_text = result.get("snippet", "")

        click.echo(f"  {i}. {title}")
        click.echo(f"     URL: {url}")
        if score:
            click.echo(f"     Score: {score:.2f}")

        # Show tags
        tags = tag_store.get_tags_for_page(url)
        if tags:
            tag_names = [t.name for t in tags]
            click.echo(f"     Tags: {', '.join(tag_names)}")

        if snippet and snippet_text:
            click.echo(f"     {snippet_text}")
        click.echo()


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def status(ctx, data_dir):
    """Show the current status of the personal-index system.

    Displays statistics about indexed pages, interests, tags, and configuration.
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    store = get_interest_store(dd)
    tag_store = get_tag_store(dd)

    click.echo("personal-index Status")
    click.echo("=" * 40)
    click.echo(f"Data directory: {dd}")
    click.echo()

    # Index stats
    page_count = idx.get_page_count()
    click.echo(f"Indexed pages: {page_count}")

    # Interest stats
    all_interests = store.list_all()
    enabled_interests = store.get_enabled()
    click.echo(f"Interests: {len(all_interests)} total, {len(enabled_interests)} enabled")
    if all_interests:
        for interest in enabled_interests:
            click.echo(f"  - {interest.name} (priority: {interest.priority})")

    # Tag stats
    tag_count = tag_store.get_tag_count()
    tagged_pages = tag_store.get_tagged_page_count()
    click.echo(f"Tags: {tag_count} tags, {tagged_pages} tagged pages")

    # Config
    config_path = "config.yaml"
    if os.path.exists(config_path):
        click.echo(f"Config: {config_path}")
    else:
        click.echo("Config: not found (run 'personal-index init' to create)")


@main.command("import-files")
@click.argument("paths", nargs=-1, required=True)
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directories")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def import_files(ctx, paths, recursive, data_dir):
    """Import local files into the index.

    Reads files from the given paths, extracts content, filters by interests,
    scores, tags, and indexes them.

    Examples:
        personal-index import ./articles/
        personal-index import -r ./docs/
        personal-index import file1.md file2.txt
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.pipeline_runner import PipelineRunner
    from personal_index.models import CrawledPage

    runner = PipelineRunner(data_dir=dd)
    imported = 0
    skipped = 0
    errors = 0

    for path in paths:
        if not os.path.exists(path):
            click.echo(f"Warning: path not found: {path}", err=True)
            errors += 1
            continue

        if os.path.isfile(path):
            files = [path]
        elif os.path.isdir(path) and recursive:
            files = []
            for root, dirs, filenames in os.walk(path):
                for fn in filenames:
                    if fn.startswith("."):
                        continue
                    files.append(os.path.join(root, fn))
        elif os.path.isdir(path):
            files = [os.path.join(path, f) for f in os.listdir(path)
                     if os.path.isfile(os.path.join(path, f)) and not f.startswith(".")]
        else:
            continue

        for fp in files:
            try:
                with open(fp, "r", errors="replace") as f:
                    content = f.read()
                if len(content) < 10:
                    skipped += 1
                    continue
                url = f"file://{os.path.abspath(fp)}"
                page = CrawledPage(
                    url=url,
                    title=os.path.basename(fp),
                    content=content,
                )
                if runner.add_page_directly(page):
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                click.echo(f"Error importing {fp}: {e}", err=True)
                errors += 1

    click.echo(f"Import complete: {imported} imported, {skipped} skipped, {errors} errors")


# Also register as 'import' alias
main.add_command(import_files, "import")


@main.group()
def tags():
    """Manage content tags."""


@tags.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_list(ctx, data_dir):
    """List all tags."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    tag_store = get_tag_store(dd)
    all_tags = tag_store.list_tags()
    if not all_tags:
        click.echo("No tags found.")
        return
    for tag in all_tags:
        page_count = len(tag_store.get_pages_for_tag(tag.name))
        click.echo(f"  {tag.name}: {page_count} page(s)")


@tags.command("add")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_add(ctx, tag_name, url, data_dir):
    """Add a tag to a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    tag_store = get_tag_store(dd)
    tag_store.add_tag_to_page(url, tag_name)
    click.echo(f"Added tag '{tag_name}' to {url}")


@tags.command("remove")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_remove(ctx, tag_name, url, data_dir):
    """Remove a tag from a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    tag_store = get_tag_store(dd)
    if tag_store.remove_tag_from_page(url, tag_name):
        click.echo(f"Removed tag '{tag_name}' from {url}")
    else:
        click.echo(f"Tag '{tag_name}' not found on {url}", err=True)
        sys.exit(1)


@tags.command("pages")
@click.argument("tag_name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_pages(ctx, tag_name, data_dir):
    """List all pages with a given tag."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    tag_store = get_tag_store(dd)
    pages = tag_store.get_pages_for_tag(tag_name)
    if not pages:
        click.echo(f"No pages tagged with '{tag_name}'.")
        return
    click.echo(f"Pages tagged with '{tag_name}':")
    for page_url in pages:
        click.echo(f"  {page_url}")


@main.group()
def schedule():
    """Manage scheduled crawl jobs."""


@schedule.command("add")
@click.option("-n", "--name", required=True, help="Job name")
@click.option("-u", "--url", required=True, help="URL to crawl")
@click.option("-i", "--interval", default=24, type=int, help="Interval in hours")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_add(ctx, name, url, interval, data_dir):
    """Add a scheduled crawl job."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    idx = get_search_index(dd)
    from personal_index.scheduler import ScheduleStore
    sched_store = ScheduleStore(store_path=f"{dd}/schedule.json")
    scheduler = Scheduler(interest_store=store, search_index=idx, schedule_store=sched_store)
    scheduler.add_job(name=name, url=url, interval_hours=interval)
    click.echo(f"Added scheduled job: {name} (every {interval}h)")


@schedule.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_list(ctx, data_dir):
    """List all scheduled jobs."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    idx = get_search_index(dd)
    from personal_index.scheduler import ScheduleStore
    sched_store = ScheduleStore(store_path=f"{dd}/schedule.json")
    scheduler = Scheduler(interest_store=store, search_index=idx, schedule_store=sched_store)
    jobs = scheduler.list_jobs()
    if not jobs:
        click.echo("No scheduled jobs.")
        return
    for job in jobs:
        click.echo(f"  {job.name}: {job.url} (every {job.interval_hours}h)")


@schedule.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_remove(ctx, name, data_dir):
    """Remove a scheduled job by name."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    idx = get_search_index(dd)
    from personal_index.scheduler import ScheduleStore
    sched_store = ScheduleStore(store_path=f"{dd}/schedule.json")
    scheduler = Scheduler(interest_store=store, search_index=idx, schedule_store=sched_store)
    if scheduler.remove_job(name):
        click.echo(f"Removed scheduled job: {name}")
    else:
        click.echo(f"Job not found: {name}", err=True)
        sys.exit(1)


@click.group()
def config():
    """View and modify configuration."""


@config.command("show")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_show(ctx, data_dir):
    """Show current configuration."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        click.echo("Current configuration:")
        click.echo(f"  Data dir: {data.get('data_dir', dd)}")
        crawler = data.get("crawler", {})
        click.echo(f"  Max depth: {crawler.get('max_depth', 3)}")
        click.echo(f"  Politeness delay: {crawler.get('politeness_delay', 1.0)}s")
        click.echo(f"  Rate limit: {crawler.get('rate_limit', 10)}/s")
        scheduler = data.get("scheduler", {})
        click.echo(f"  Scheduler enabled: {scheduler.get('enabled', False)}")
        click.echo(f"  Interval: {scheduler.get('interval_hours', 24)}h")
    else:
        click.echo("No config file found. Run 'personal-index init' first.")


@config.command("set-crawler")
@click.option("--max-depth", type=int, help="Set max crawl depth")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_set_crawler(ctx, max_depth, data_dir):
    """Set crawler configuration."""
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        click.echo("No config file found. Run 'personal-index init' first.", err=True)
        sys.exit(1)
    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}
    if max_depth is not None:
        data.setdefault("crawler", {})["max_depth"] = max_depth
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    click.echo("Crawler configuration updated.")


@config.command("set-schedule")
@click.option("--interval", type=int, help="Set schedule interval in hours")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_set_schedule(ctx, interval, data_dir):
    """Set scheduler configuration."""
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        click.echo("No config file found. Run 'personal-index init' first.", err=True)
        sys.exit(1)
    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}
    if interval is not None:
        data.setdefault("scheduler", {})["interval_hours"] = interval
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    click.echo("Scheduler configuration updated.")
