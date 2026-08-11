"""CLI entry point for personal-index.

Provides commands for crawling, indexing, searching, and managing
a personal web content index.

Usage:
    personal-index init
    personal-index crawl https://example.com
    personal-index pipeline https://example.com
    personal-index search "python tutorial"
    personal-index export --format markdown
"""

from __future__ import annotations

import json
import os
import shutil
import sys

import click
import yaml

from personal_index.cli_crawl import crawl as crawl_cmd
from personal_index.cli_extract import extract as extract_cmd
from personal_index.cli_clear import clear as clear_cmd
from personal_index.cli_doctor import doctor as doctor_cmd
from personal_index.cli_list import list_pages as list_cmd
from personal_index.cli_remove import remove_page as remove_cmd
from personal_index.cli_search import search as search_cmd
from personal_index.cli_stats import stats as stats_cmd
from personal_index.cli_status import status as status_cmd
from personal_index.cli_top import top_pages as top_cmd
from personal_index.cli_verify import verify as verify_cmd
from personal_index.cli_watch import watch as watch_cmd
from personal_index.index import SearchIndex
from personal_index.tags import TagStore


def get_search_index(data_dir: str) -> SearchIndex:
    """Get or create a search index for the given data directory."""
    db_path = os.path.join(data_dir, "search_index.json")
    return SearchIndex(db_path=db_path)


def get_tag_store(data_dir: str) -> TagStore:
    """Get or create a tag store for the given data directory."""
    store_path = os.path.join(data_dir, "tags.json")
    return TagStore(store_path=store_path)


def get_interest_store(data_dir: str):
    """Get or create an interest store for the given data directory."""
    from personal_index.interests import InterestStore
    store_path = os.path.join(data_dir, "interests.json")
    return InterestStore(store_path=store_path)


def load_config(data_dir: str) -> dict:
    """Load configuration from config.yaml."""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


@click.group(cls=click.Group, invoke_without_command=True)
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.version_option(version="0.1.0", prog_name="personal-index")
@click.pass_context
def main(ctx, data_dir, verbose):
    """Personal Index - Crawl, filter, score, tag, and search the web.

    A personal web search engine that scans, filters, and indexes
    the web based on your interests.

    Quick start:
        personal-index init
        personal-index interests add programming --keywords "python,javascript,web"
        personal-index pipeline https://example.com
        personal-index search "python"
    """
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir or ".personal_index"
    ctx.obj["verbose"] = verbose


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--config", default=None, help="Config file path")
@click.pass_context
def init(ctx, data_dir, config):
    """Initialize a new personal-index project.

    Creates the data directory and a default configuration file.

    Examples:
        personal-index init
        personal-index init --data-dir ~/my-index
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)
    os.makedirs(os.path.join(dd, "cache"), exist_ok=True)
    os.makedirs(os.path.join(dd, "archive"), exist_ok=True)
    os.makedirs(os.path.join(dd, "backups"), exist_ok=True)

    # Create default config if not exists
    config_path = config or "config.yaml"
    if not os.path.exists(config_path):
        default_config = {
            "crawler": {
                "max_depth": 3,
                "max_pages": 100,
                "timeout": 30,
                "delay": 1.0,
            },
            "filter": {
                "min_content_length": 100,
                "require_interest_match": False,
            },
            "scoring": {
                "min_score_threshold": 0.0,
            },
            "scheduler": {
                "interval_hours": 24,
            },
        }
        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        click.echo(f"Created {config_path}")

    click.echo(f"Initialized personal-index in {dd}")
    click.echo("Next steps:")
    click.echo("  1. Add interests: personal-index interests add my-interest -k keyword1 -k keyword2")
    click.echo("  2. Run pipeline: personal-index pipeline https://example.com")
    click.echo("  3. Search: personal-index search 'keyword'")


@main.command()
@click.argument("url")
@click.option("--depth", "-d", default=3, type=int, help="Max crawl depth")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--timeout", "-t", default=30, type=int, help="Request timeout in seconds")
@click.option("--delay", default=1.0, type=float, help="Delay between requests")
@click.option("--max-pages", "-m", default=100, type=int, help="Max pages to crawl")
@click.pass_context
def crawl(ctx, url, depth, data_dir, timeout, delay, max_pages):
    """Crawl a URL and its linked pages.

    Crawls the given URL and follows links up to the specified depth.
    Results are stored in the data directory.

    Examples:
        personal-index crawl https://example.com
        personal-index crawl https://example.com -d 2 -m 50
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    from personal_index.crawler.main import Crawler, CrawlerConfig
    from personal_index.interests import InterestStore

    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    config = CrawlerConfig(
        max_depth=depth,
        max_pages=max_pages,
        delay=delay,
        timeout=timeout,
    )

    crawler = Crawler(config=config, interest_store=interest_store)
    pages = crawler.crawl(url)

    click.echo(f"Crawled {len(pages)} pages from {url}")

    # Save crawled pages
    cache_path = os.path.join(dd, "cache", "crawled.json")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump([p.to_dict() for p in pages], f, indent=2, default=str)

    click.echo(f"Saved to {cache_path}")


@main.command()
@click.argument("query")
@click.option("--limit", "-l", default=20, type=int, help="Max results")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json", "csv"]),
              help="Output format")
@click.pass_context
def search(ctx, query, limit, tag, data_dir, fmt):
    """Search the indexed content.

    Searches through all indexed pages for the given query.
    Results are ranked by relevance score.

    Examples:
        personal-index search "python tutorial"
        personal-index search "web development" --limit 10
        personal-index search "api" --tag documentation
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)

    results = idx.search(query, limit=limit)

    # Filter by tag if specified
    if tag:
        tag_store = get_tag_store(dd)
        tagged_urls = set(tag_store.get_pages_for_tag(tag))
        results = [r for r in results if r.url in tagged_urls]

    if not results:
        click.echo(f"No results found for '{query}'")
        return

    if fmt == "json":
        click.echo(json.dumps([r.to_dict() for r in results], indent=2, default=str))
    elif fmt == "csv":
        click.echo("Rank,URL,Title,Score,Snippet")
        for i, r in enumerate(results, 1):
            snippet = (r.snippet or "")[:100].replace('"', '""')
            click.echo(f'{i},"{r.url}","{r.title}","{r.relevance_score:.4f}","{snippet}"')
    else:
        click.echo(f"\nSearch results for '{query}' ({len(results)} found):")
        click.echo("-" * 60)
        for i, r in enumerate(results, 1):
            click.echo(f"\n{i}. {r.title or r.url}")
            click.echo(f"   {r.url}")
            click.echo(f"   Score: {r.relevance_score:.4f}")
            if r.snippet:
                click.echo(f"   {r.snippet[:200]}")
            # Tags available via: personal-index tags list


@main.group()
@click.pass_context
def interests(ctx):
    """Manage your content interests.

    Interests define what topics and keywords you want to track.
    Pages matching your interests get higher scores.

    Examples:
        personal-index interests add programming -k python -k javascript
        personal-index interests list
        personal-index interests remove programming
    """


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keywords", multiple=True, help="Keywords to match")
@click.option("--priority", default=5, type=int, help="Priority (1-10)")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_add(ctx, name, keywords, priority, data_dir):
    """Add a new interest to track."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.models import Interest

    store = get_interest_store(dd)
    interest = Interest(
        name=name,
        keywords=list(keywords),
        priority=priority,
    )
    store.add(interest)
    click.echo(f"Added interest: {name}")


@interests.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_list(ctx, data_dir):
    """List all configured interests."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    interests_list = store.list_all()

    if not interests_list:
        click.echo("No interests configured.")
        return

    click.echo(f"Interests ({len(interests_list)}):")
    for interest in interests_list:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  {interest.name} ({status}) - priority: {interest.priority}")
        if interest.keywords:
            click.echo(f"    Keywords: {', '.join(interest.keywords)}")


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
        click.echo(f"Interest '{name}' not found", err=True)
        sys.exit(1)


@main.group()
@click.pass_context
def tags(ctx):
    """Manage content tags.

    Tags help organize and categorize your indexed content.

    Examples:
        personal-index tags add important https://example.com/page
        personal-index tags list
        personal-index tags remove important https://example.com/page
    """


@tags.command("add")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_add(ctx, tag_name, url, data_dir):
    """Add a tag to a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    store.add_tag_to_page(url, tag_name)
    click.echo(f"Added tag '{tag_name}' to {url}")


@tags.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_list(ctx, data_dir):
    """List all tags."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    tags = store.list_tags()

    if not tags:
        click.echo("No tags configured.")
        return

    click.echo(f"Tags ({len(tags)}):")
    for tag in tags:
        page_count = len(store.get_pages_for_tag(tag.name))
        click.echo(f"  {tag} ({page_count} pages)")


@tags.command("remove")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_remove(ctx, tag_name, url, data_dir):
    """Remove a tag from a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    store.remove_tag_from_page(url, tag_name)
    click.echo(f"Removed tag '{tag_name}' from {url}")


@main.command("import")
@click.argument("source")
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directories")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def import_(ctx, source, recursive, data_dir):
    """Import local files into the index.

    Imports text files, markdown files, and HTML files into the
    search index. Supports recursive directory import.

    Examples:
        personal-index import ./article.txt
        personal-index import ./docs/ --recursive
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    from personal_index.config.pipeline_config import PipelineConfig
    from personal_index.pipeline_runner import PipelineRunner

    config = PipelineConfig(
        min_score_threshold=0.0,
        min_content_length=10,
    )

    runner = PipelineRunner(
        data_dir=dd,
        pipeline_config=config,
    )

    files = []
    if os.path.isdir(source):
        for root, dirs, filenames in os.walk(source):
            for fn in filenames:
                fp = os.path.join(root, fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext in ('.txt', '.md', '.rst', '.html', '.htm', '.json', '.xml'):
                    files.append(fp)
    elif os.path.isfile(source):
        files.append(source)
    else:
        click.echo(f"Source not found: {source}", err=True)
        sys.exit(1)

    if not files:
        click.echo("No importable files found.")
        return

    stats = runner.run_from_files(files)
    click.echo(f"\nImport complete: {len(files)} file(s) processed")
    click.echo(f"  Indexed: {stats.pages_indexed}")
    click.echo(f"  Filtered out: {stats.pages_filtered_out}")
    click.echo(f"  Errors: {len(stats.errors)}")

    runner.close()


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def status(ctx, data_dir):
    """Show the current status of your index.

    Displays statistics about indexed pages, tags, and interests.

    Examples:
        personal-index status
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    # Calculate storage size
    total_size = 0
    for root, dirs, files in os.walk(dd):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                pass

    size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / (1024*1024):.1f} MB"

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"  Data directory: {dd}")
    click.echo(f"  Storage used:   {size_str}")
    click.echo()
    click.echo("Index:")
    click.echo(f"  Pages indexed:  {idx.get_page_count()}")
    click.echo()
    click.echo("Tags:")
    click.echo(f"  Unique tags:    {tag_store.get_tag_count()}")
    click.echo(f"  Tagged pages:   {tag_store.get_tagged_page_count()}")
    click.echo()
    click.echo("Interests:")
    click.echo(f"  Total interests: {len(interest_store.list_all())}")


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def reset(ctx, data_dir):
    """Reset the index to a clean state.

    Removes all indexed data, tags, and cache.
    Interests and configuration are preserved.

    Examples:
        personal-index reset
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    # Remove index files
    for f in ["search_index.json", "tags.json"]:
        fp = os.path.join(dd, f)
        if os.path.exists(fp):
            os.remove(fp)
            click.echo(f"Removed {fp}")

    # Remove cache and archive
    for d in ["cache", "archive"]:
        dp = os.path.join(dd, d)
        if os.path.exists(dp):
            shutil.rmtree(dp)
            click.echo(f"Removed {dp}")

    click.echo("Index reset complete.")


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def validate(ctx, data_dir):
    """Validate the integrity of your index.

    Checks for corrupted data, missing files, and consistency issues.

    Examples:
        personal-index validate
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    issues = []
    warnings = []

    # Check data directory
    if not os.path.exists(dd):
        issues.append(f"Data directory '{dd}' does not exist")
    else:
        # Check index file
        idx_path = os.path.join(dd, "search_index.json")
        if os.path.exists(idx_path):
            try:
                with open(idx_path, "r") as f:
                    data = json.load(f)
                if "pages" not in data:
                    issues.append("Index file missing 'pages' key")
                if "word_index" not in data:
                    issues.append("Index file missing 'word_index' key")
            except json.JSONDecodeError:
                issues.append("Index file is corrupted (invalid JSON)")
        else:
            warnings.append("No index file found (run 'personal-index pipeline' first)")

        # Check tags file
        tags_path = os.path.join(dd, "tags.json")
        if os.path.exists(tags_path):
            try:
                with open(tags_path, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                issues.append("Tags file is corrupted (invalid JSON)")

        # Check interests file
        interests_path = os.path.join(dd, "interests.json")
        if os.path.exists(interests_path):
            try:
                with open(interests_path, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                issues.append("Interests file is corrupted (invalid JSON)")

    click.echo("Validation Results")
    click.echo("=" * 40)

    if issues:
        click.echo(f"\n✗ Issues ({len(issues)}):")
        for issue in issues:
            click.echo(f"  - {issue}")
    else:
        click.echo("\n✓ No critical issues found")

    if warnings:
        click.echo(f"\n⚠ Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"  - {warning}")

    if issues:
        sys.exit(1)


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def reindex(ctx, data_dir):
    """Rebuild the search index from existing data.

    Rebuilds the inverted index from the stored pages.
    Useful after upgrading or if the index becomes corrupted.

    Examples:
        personal-index reindex
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)

    page_count = idx.get_page_count()
    if page_count == 0:
        click.echo("No pages to reindex.")
        return

    # Force rebuild by clearing and re-adding
    idx.clear()
    # Reload from file and rebuild word index
    idx._load()
    for url, page in idx._pages.items():
        idx._add_to_word_index(url, page)

    click.echo(f"Reindexed {page_count} pages")


@main.command()
@click.option("--format", "fmt", default="markdown",
              type=click.Choice(["markdown", "json", "csv"]),
              help="Export format")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def export(ctx, fmt, output, data_dir):
    """Export indexed content.

    Exports all indexed pages in the specified format.

    Examples:
        personal-index export --format markdown
        personal-index export --format json -o results.json
        personal-index export --format csv
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    pages = idx.list_pages()
    if not pages:
        click.echo("No indexed content to export.")
        return

    if fmt == "markdown":
        lines = ["# Search Results", ""]
        for page in pages:
            tags = tag_store.get_tags_for_page(page.url)
            lines.append(f"## {page.title or page.url}")
            lines.append(f"- **URL**: {page.url}")
            lines.append(f"- **Score**: {page.score:.4f}")
            if tags:
                lines.append(f"- **Tags**: {', '.join(t.name if hasattr(t, 'name') else str(t) for t in tags)}")
            if page.content:
                lines.append(f"- **Snippet**: {page.content[:200]}...")
            lines.append("")
        output_text = "\n".join(lines)
    elif fmt == "json":
        output_text = json.dumps(
            [p.to_dict() for p in pages],
            indent=2,
            default=str,
        )
    else:  # csv
        lines = ["URL,Title,Score,Content"]
        for page in pages:
            content = (page.content or "").replace('"', '""')[:500]
            title = (page.title or "").replace('"', '""')
            lines.append(f'"{page.url}","{title}","{page.score:.4f}","{content}"')
        output_text = "\n".join(lines)

    if output:
        with open(output, "w") as f:
            f.write(output_text)
        click.echo(f"Exported {len(pages)} pages to {output}")
    else:
        click.echo(output_text)


@main.group()
@click.pass_context
def config(ctx):
    """Manage configuration settings.

    View and modify crawler, filter, and scheduler settings.

    Examples:
        personal-index config show
        personal-index config set-crawler --max-depth 5
    """


@config.command("show")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_show(ctx, data_dir):
    """Show current configuration."""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        click.echo("Current configuration:")
        click.echo(yaml.dump(data, default_flow_style=False))
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


# Schedule management commands
@main.group()
@click.pass_context
def schedule(ctx):
    """Manage scheduled crawl jobs.

    Schedule regular crawls of your favorite sites.

    Examples:
        personal-index schedule add daily --url https://example.com --interval 24
        personal-index schedule list
        personal-index schedule remove daily
    """


@schedule.command("add")
@click.option("-n", "--name", required=True, help="Job name")
@click.option("--url", "-u", required=True, help="URL to crawl")
@click.option("--interval", "-i", default=24, type=int, help="Interval in hours")
@click.option("--depth", "-d", default=2, type=int, help="Crawl depth")
@click.option("--max-pages", "-m", default=50, type=int, help="Max pages per run")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_add(ctx, name, url, interval, depth, max_pages, data_dir):
    """Add a new scheduled crawl job."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleConfig, ScheduleEntry, ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)

    existing = store.list_all()
    if any(e.name == name for e in existing):
        click.echo(f"Scheduled job '{name}' already exists.", err=True)
        sys.exit(1)

    config = ScheduleConfig(
        interval_hours=interval,
        seed_urls=[url],
        max_pages_per_run=max_pages,
        crawl_depth=depth,
    )
    entry = ScheduleEntry(name=name, config=config)
    store.add(entry)
    click.echo(f"Added scheduled job '{name}'")


@schedule.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_list(ctx, data_dir):
    """List all scheduled crawl jobs."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)
    entries = store.list_all()

    if not entries:
        click.echo("No scheduled jobs configured.")
        return

    click.echo(f"Scheduled jobs ({len(entries)}):")
    for entry in entries:
        click.echo(f"  {entry.name}: every {entry.config.interval_hours}h, "
                    f"urls={', '.join(entry.config.seed_urls)}, "
                    f"runs={entry.run_count}")


@schedule.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_remove(ctx, name, data_dir):
    """Remove a scheduled crawl job."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)

    if store.remove(name):
        click.echo(f"Removed scheduled job '{name}'")
    else:
        click.echo(f"Scheduled job '{name}' not found", err=True)
        sys.exit(1)


@schedule.command("run")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_run(ctx, name, data_dir):
    """Manually run a scheduled job now."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)

    entries = store.list_all()
    entry = next((e for e in entries if e.name == name), None)
    if not entry:
        click.echo(f"Scheduled job '{name}' not found", err=True)
        sys.exit(1)

    click.echo(f"Running scheduled job '{name}'...")

    from personal_index.pipeline_runner import PipelineConfig, PipelineRunner
    config = PipelineConfig(
        max_depth=entry.config.crawl_depth,
        max_pages=entry.config.max_pages_per_run,
    )
    runner = PipelineRunner(data_dir=dd, pipeline_config=config)
    try:
        stats = runner.run(entry.config.seed_urls)
        click.echo(f"  Crawled: {stats.pages_crawled}")
        click.echo(f"  Indexed: {stats.pages_indexed}")
        click.echo(f"  Errors: {len(stats.errors)}")
    finally:
        runner.close()


# Import pipeline command
from personal_index.cli_pipeline import pipeline

main.add_command(pipeline)

# Doctor command
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def doctor(ctx, data_dir):
    """Diagnose issues with your personal-index setup.

    Checks configuration, data directory, and component health.

    Examples:
        personal-index doctor
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    issues = []
    warnings = []

    # Check data directory
    if not os.path.exists(dd):
        issues.append(f"Data directory '{dd}' does not exist. Run 'personal-index init'.")
    else:
        # Check subdirectories
        for subdir in ["cache", "archive", "backups"]:
            if not os.path.exists(os.path.join(dd, subdir)):
                warnings.append(f"Missing subdirectory: {subdir}")

    # Check config
    if not os.path.exists("config.yaml"):
        warnings.append("No config.yaml found. Run 'personal-index init' to create one.")

    # Check index
    idx = get_search_index(dd)
    if idx.get_page_count() == 0:
        warnings.append("No pages indexed. Run 'personal-index pipeline' to index content.")

    # Check interests
    interest_store = get_interest_store(dd)
    if not interest_store.list_all():
        warnings.append("No interests configured. Add interests for better scoring.")

    # Check tag store
    tag_store = get_tag_store(dd)

    click.echo("Personal Index Health Check")
    click.echo("=" * 40)

    if issues:
        click.echo(f"\n✗ Issues ({len(issues)}):")
        for issue in issues:
            click.echo(f"  - {issue}")
    else:
        click.echo("\n✓ No critical issues found")

    if warnings:
        click.echo(f"\n⚠ Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"  - {warning}")

    click.echo(f"\nIndex: {idx.get_page_count()} pages")
    click.echo(f"Tags: {tag_store.get_tag_count()}")
    click.echo(f"Interests: {len(interest_store.list_all())}")

    if issues:
        sys.exit(1)


main.add_command(stats_cmd)
main.add_command(list_cmd)
main.add_command(remove_cmd)
main.add_command(clear_cmd)
main.add_command(top_cmd)
main.add_command(doctor_cmd)
main.add_command(status_cmd)
main.add_command(search_cmd)
main.add_command(verify_cmd)
main.add_command(watch_cmd)
main.add_command(crawl_cmd)
main.add_command(extract_cmd)


if __name__ == "__main__":
    main()
