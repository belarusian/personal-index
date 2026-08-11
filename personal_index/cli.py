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
from personal_index.models import CrawledPage, Interest
from personal_index.scheduler import Scheduler


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
def add_interest(ctx, name, keyword, url_pattern, priority, data_dir):
    """Add a new interest to track.

    Example: personal-index interests add -n python -k python -k programming -p 8
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    interest = Interest(
        name=name,
        keywords=list(keyword),
        url_patterns=list(url_pattern),
        priority=priority,
    )
    store.add(interest)
    click.echo(f"Added interest: {name} (priority={priority})")
    if keyword:
        click.echo(f"  Keywords: {', '.join(keyword)}")


@interests.command("list")
@click.option("--all", "show_all", is_flag=True, help="Show disabled interests too")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def list_interests(ctx, show_all, data_dir):
    """List all tracked interests."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    all_interests = store.list_all()
    if not all_interests:
        click.echo("No interests configured.")
        click.echo("Add one with: personal-index interests add -n mytopic -k keyword1 -k keyword2")
        return
    for interest in all_interests:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  {interest.name} [{status}] priority={interest.priority}")
        if interest.keywords:
            click.echo(f"    keywords: {', '.join(interest.keywords)}")
        if interest.url_patterns:
            click.echo(f"    url patterns: {', '.join(interest.url_patterns)}")


@interests.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def remove_interest(ctx, name, data_dir):
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
def enable_interest(ctx, name, data_dir):
    """Enable a disabled interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    if store.enable(name):
        click.echo(f"Enabled interest: {name}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        sys.exit(1)


@interests.command("disable")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def disable_interest(ctx, name, data_dir):
    """Disable an interest without removing it."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    if store.disable(name):
        click.echo(f"Disabled interest: {name}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        sys.exit(1)


@main.command()
@click.argument("query")
@click.option("-n", "--limit", default=20, type=int, help="Max results")
@click.option("-p", "--page", default=1, type=int, help="Page number")
@click.option("--snippet", is_flag=True, help="Show content snippets")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def search(ctx, query, limit, page, snippet, data_dir):
    """Search indexed content.

    Searches through all indexed pages for the given query terms.
    Results are ranked by relevance score.

    Example: personal-index search "python programming" --snippet
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)

    results = index.search(query, limit=limit)

    if not results:
        click.echo(f"No results found for: {query}")
        click.echo("Try: personal-index import ./files/  or  personal-index pipeline https://example.com")
        return

    click.echo(f"Found {len(results)} result(s) for '{query}':")
    click.echo("")
    for i, r in enumerate(results, 1):
        click.echo(f"  {i}. {r.title}")
        click.echo(f"     {r.url}")
        if r.relevance_score:
            click.echo(f"     Score: {r.relevance_score:.2f}")
        if snippet and r.snippet:
            click.echo(f"     {r.snippet[:200]}")
        click.echo("")


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def status(ctx, data_dir):
    """Show current index status and statistics.

    Displays information about indexed pages, interests, and tags.
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)
    store = get_interest_store(dd)

    click.echo("=== Personal Index Status ===")
    click.echo(f"  Data directory: {dd}")
    click.echo(f"  Indexed pages: {index.get_page_count()}")
    click.echo(f"  Interests: {len(store.list_all())}")

    # Show top domains
    pages = index.list_pages()
    if pages:
        domains = {}
        for p in pages:
            d = getattr(p, "domain", "unknown")
            domains[d] = domains.get(d, 0) + 1
        click.echo(f"  Domains: {len(domains)}")
        for domain, count in sorted(domains.items(), key=lambda x: -x[1])[:5]:
            click.echo(f"    {domain}: {count} page(s)")

    click.echo("")
    click.echo("Interests:")
    for interest in store.list_all():
        click.echo(f"  - {interest.name} (priority={interest.priority})")

    # Show tags
    from personal_index.tags import TagStore
    tag_store = TagStore(store_path=f"{dd}/tags.json")
    tags = tag_store.list_tags()
    if tags:
        click.echo("")
        click.echo("Tags:")
        for tag in tags:
            click.echo(f"  - {tag.name}")


@main.command()
@click.argument("path")
@click.option("-r", "--recursive", is_flag=True, help="Recursively import directories")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def import_cmd(ctx, path, recursive, data_dir):
    """Import local files into the index.

    Imports text files, markdown, and other readable content into the search index.
    Use --recursive to import entire directory trees.

    Example: personal-index import ./articles/ --recursive
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)

    if not os.path.exists(path):
        click.echo(f"Path not found: {path}", err=True)
        sys.exit(1)

    paths_to_import = []
    p = os.path.abspath(path)
    if os.path.isfile(p):
        paths_to_import.append(p)
    elif os.path.isdir(p):
        if recursive:
            for root, dirs, files in os.walk(p):
                for f in sorted(files):
                    paths_to_import.append(os.path.join(root, f))
        else:
            for f in sorted(os.listdir(p)):
                fp = os.path.join(p, f)
                if os.path.isfile(fp):
                    paths_to_import.append(fp)

    imported = 0
    for file_path in paths_to_import:
        try:
            with open(file_path, "r", errors="replace") as f:
                text = f.read()
            page = CrawledPage(
                url=f"file://{file_path}",
                title=os.path.basename(file_path),
                content=text,
            )
            index.add_page(page)
            imported += 1
        except Exception as e:
            click.echo(f"  Error importing {file_path}: {e}", err=True)

    click.echo(f"Imported {imported} file(s) into index.")
    if imported > 0:
        click.echo(f"Total indexed pages: {index.get_page_count()}")


@main.command()
@click.option("-f", "--format", "fmt", default="markdown", type=click.Choice(["markdown", "json", "csv"]), help="Export format")
@click.option("-o", "--output", default=None, help="Output file path")
@click.option("-q", "--query", default=None, help="Only export matching results")
@click.option("-l", "--limit", default=100, type=int, help="Max items to export")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def export_cmd(ctx, fmt, output, query, limit, data_dir):
    """Export indexed content to a file.

    Exports can be filtered with --query and limited with --limit.
    Supports markdown, JSON, and CSV formats.

    Example: personal-index export -f json -o results.json -q python
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)

    if query:
        results = index.search(query, limit=limit)
    else:
        results = index.list_pages()[:limit]

    if not results:
        if fmt == "json":
            click.echo("[]")
        elif fmt == "csv":
            click.echo("title,url,snippet,score")
        else:
            click.echo("No content to export.")
        return

    if fmt == "markdown":
        lines = ["# Exported Content", ""]
        for r in results:
            lines.append(f"## {r.title}")
            lines.append(f"**URL:** {r.url}")
            if hasattr(r, 'score') and r.score:
                lines.append(f"**Score:** {r.score:.2f}")
            snippet = getattr(r, "snippet", "")
            if snippet:
                lines.append(snippet)
            lines.append("")
        content = "\n".join(lines)
    elif fmt == "json":
        data = []
        for r in results:
            item = {
                "title": r.title,
                "url": r.url,
                "snippet": getattr(r, 'snippet', ''),
                "score": getattr(r, 'score', 0),
            }
            data.append(item)
        content = json.dumps(data, indent=2)
    else:  # csv
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["title", "url", "snippet", "score"])
        for r in results:
            writer.writerow([r.title, r.url, getattr(r, 'snippet', ''), getattr(r, 'score', 0)])
        content = buf.getvalue()

    if output:
        with open(output, "w") as f:
            f.write(content)
        click.echo(f"Exported {len(results)} items to {output}")
    else:
        click.echo(content)


@main.group()
def tag():
    """Manage content tags.

    Tags are used to categorize and organize indexed content.
    """


@tag.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def list_tags(ctx, data_dir):
    """List all defined tags."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.tags import TagStore
    store = TagStore(store_path=f"{dd}/tags.json")
    tags = store.list_tags()
    if not tags:
        click.echo("No tags defined.")
        return
    for tag in tags:
        click.echo(f"  {tag.name} ({tag.color})")


@tag.command("add")
@click.argument("name")
@click.option("--color", default="#3498db", help="Tag color hex")
@click.option("--description", default="", help="Tag description")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def add_tag(ctx, name, color, description, data_dir):
    """Add a new tag."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.tags import TagStore
    store = TagStore(store_path=f"{dd}/tags.json")
    store.create_tag(name, color=color, description=description)
    click.echo(f"Added tag: {name}")


@tag.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def remove_tag(ctx, name, data_dir):
    """Remove a tag by name."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.tags import TagStore
    store = TagStore(store_path=f"{dd}/tags.json")
    store.delete_tag(name)
    click.echo(f"Removed tag: {name}")


@main.group()
def crawl():
    """Crawl web pages and extract content.

    Standalone crawl commands for inspecting web content before indexing.
    """


@crawl.command("run")
@click.argument("urls", nargs=-1, required=True)
@click.option("-d", "--depth", default=3, type=int, help="Crawl depth")
@click.option("--max-pages", default=50, type=int, help="Maximum pages to crawl")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def crawl_run(ctx, urls, depth, max_pages, data_dir):
    """Crawl URLs and display extracted content without indexing.

    Useful for previewing what the pipeline would find.

    Example: personal-index crawl run https://example.com -d 2
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)

    from personal_index.crawler.main import Crawler, CrawlerConfig

    config = CrawlerConfig(
        max_depth=depth,
        max_pages=max_pages,
        delay=0.5,
    )
    crawler = Crawler(config=config, interest_store=store)
    pages = crawler.crawl(list(urls), max_depth=depth)

    click.echo(f"Crawled {len(pages)} page(s):")
    for page in pages:
        click.echo(f"\n  [{page.url}]")
        click.echo(f"  Title: {page.title}")
        content_preview = (page.content or "")[:200]
        click.echo(f"  Content: {content_preview}...")
        if page.matched_interests:
            click.echo(f"  Matched interests: {', '.join(page.matched_interests)}")


@main.group()
def index_cmd_group():
    """Manage the search index.

    Commands for inspecting and maintaining the search index.
    """


@index_cmd_group.command("count")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_count(ctx, data_dir):
    """Show the number of indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)
    click.echo(f"Indexed pages: {index.get_page_count()}")


@index_cmd_group.command("list")
@click.option("-n", "--limit", default=20, type=int, help="Max pages to list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_list(ctx, limit, data_dir):
    """List indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)
    pages = index.list_pages()[:limit]
    if not pages:
        click.echo("No indexed pages.")
        return
    for page in pages:
        click.echo(f"  {page.title} ({page.url})")


@index_cmd_group.command("remove")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_remove(ctx, url, data_dir):
    """Remove a page from the index by URL."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)
    if index.remove_page(url):
        click.echo(f"Removed: {url}")
    else:
        click.echo(f"Page not found: {url}", err=True)
        sys.exit(1)


@index_cmd_group.command("clear")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_clear(ctx, data_dir):
    """Clear all indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)
    count = index.get_page_count()
    if count == 0:
        click.echo("Index is already empty.")
        return
    for page in index.list_pages():
        index.remove_page(page.url)
    click.echo(f"Cleared {count} page(s) from index.")


main.add_command(pipeline_cmd, name="pipeline")

if __name__ == "__main__":
    main()


# Backward-compatible aliases for test imports
# These are Click groups that may not be fully implemented yet
# but need to exist for import compatibility.

@click.group()
def index():
    """Manage the search index (alias for index_cmd_group)."""


@index.command("count")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_count_alias(ctx, data_dir):
    """Show the number of indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    click.echo(f"Indexed pages: {idx.get_page_count()}")


@index.command("list")
@click.option("-n", "--limit", default=20, type=int, help="Max pages to list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_list_alias(ctx, limit, data_dir):
    """List indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    pages = idx.list_pages()[:limit]
    if not pages:
        click.echo("No indexed pages.")
        return
    for page in pages:
        click.echo(f"  {page.title} ({page.url})")


@index.command("remove")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_remove_alias(ctx, url, data_dir):
    """Remove a page from the index by URL."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    if idx.remove_page(url):
        click.echo(f"Removed: {url}")
    else:
        click.echo(f"Page not found: {url}", err=True)
        sys.exit(1)


@click.group()
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


@main.command()
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
    import os
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
                    fp = os.path.join(root, fn)
                    # Skip hidden and binary files
                    if fn.startswith("."):
                        continue
                    files.append(fp)
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
                # Use file path as URL-like identifier
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
