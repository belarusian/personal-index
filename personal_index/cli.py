"""CLI interface for personal-index."""

from __future__ import annotations

import json
import os

import click
import yaml

from personal_index.cli_pipeline import pipeline as pipeline_cmd
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import Interest
from personal_index.scheduler import Scheduler, ScheduleStore


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
    """personal-index - Track and index content matching your interests."""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir or ".personal_index"


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--config", default="config.yaml", help="Config file path")
@click.pass_context
def init(ctx, data_dir, config):
    """Initialize a new personal-index project."""
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
            "interests": [],
        }
        with open(config, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

    click.echo(f"Initialized personal-index in {data_dir}")
    click.echo("Run 'personal-index interests add' to start tracking topics.")


@main.group()
def interests():
    """Manage tracked interests."""


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keyword", multiple=True, help="Keywords to track")
@click.option("-u", "--url-pattern", multiple=True, help="URL patterns to match")
@click.option("-p", "--priority", default=5, type=int, help="Priority (1-10)")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def add_interest(ctx, name, keyword, url_pattern, priority, data_dir):
    """Add a new interest to track."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    interest = Interest(
        name=name,
        keywords=list(keyword),
        url_patterns=list(url_pattern),
        priority=priority,
    )
    store.add(interest)
    click.echo(f"Added interest: {name}")


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
        return
    for interest in all_interests:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  {interest.name} [{status}] priority={interest.priority}")
        if interest.keywords:
            click.echo(f"    keywords: {', '.join(interest.keywords)}")


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
        raise SystemExit(1)


@interests.command("toggle")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def toggle_interest(ctx, name, data_dir):
    """Toggle an interest on/off."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    interest = store.toggle(name)
    if interest:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"Interest '{name}' is now {status}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        raise SystemExit(1)


@main.command()
@click.argument("query")
@click.option("-l", "--limit", default=10, type=int, help="Max results")
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON")
@click.option("--tag", default=None, help="Filter results by tag")
@click.option("--sort", default="relevance", type=click.Choice(["relevance", "date", "title"]), help="Sort results by field")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def search(ctx, query, limit, as_json, tag, sort, data_dir):
    """Search indexed content."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)
    results = index.search(query, limit=limit)
    if not results:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No results found.")
        return
    if as_json:
        data = []
        for r in results:
            data.append({
                "title": r.title,
                "url": r.url,
                "snippet": getattr(r, "snippet", ""),
                "score": getattr(r, "score", 0),
            })
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Found {len(results)} results for '{query}':\n")
        for i, r in enumerate(results, 1):
            click.echo(f"  {i}. {r.title}")
            click.echo(f"     {r.url}")
            if getattr(r, "snippet", ""):
                click.echo(f"     {r.snippet}")
            click.echo()


@main.command()
@click.argument("url")
@click.option("-d", "--depth", default=1, type=int, help="Crawl depth")
@click.option("--no-index", is_flag=True, help="Don't index crawled pages")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def crawl(ctx, url, depth, no_index, data_dir):
    """Crawl a URL and optionally index it."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.crawler.main import Crawler, CrawlerConfig
    from personal_index.interests import InterestStore

    interest_store = get_interest_store(dd)
    crawler = Crawler(
        config=CrawlerConfig(max_depth=depth),
        interest_store=interest_store,
    )
    click.echo(f"Crawling {url} (depth={depth})...")
    try:
        pages = crawler.crawl([url], max_depth=depth)
        click.echo(f"Crawled {len(pages)} page(s)")
        if not no_index:
            index = get_search_index(dd)
            for page in pages:
                index.add_page(page)
            click.echo(f"Indexed {len(pages)} page(s)")
    except Exception as e:
        click.echo(f"Crawl error: {e}", err=True)


@main.group()
def index():
    """Manage the search index."""


@index.command("count")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_count(ctx, data_dir):
    """Show number of indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    click.echo(f"Indexed pages: {idx.get_page_count()}")


@index.command("rebuild")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_rebuild(ctx, data_dir):
    """Rebuild the search index from scratch."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    pages = idx.list_pages()
    idx.clear()
    for page in pages:
        idx.add_page(page)
    click.echo(f"Index rebuild complete. {idx.get_page_count()} pages indexed.")


@index.command("list")
@click.option("-l", "--limit", default=20, type=int, help="Max pages to list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_list(ctx, limit, data_dir):
    """List indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    pages = idx.list_pages()[:limit]
    if not pages:
        click.echo("No pages indexed.")
        return
    for page in pages:
        click.echo(f"  {page.title} ({page.url})")


@index.command("clear")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_clear(ctx, data_dir):
    """Clear the entire search index."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    idx.clear()
    click.echo("Index cleared.")


@index.command("remove")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def index_remove(ctx, url, data_dir):
    """Remove a page from the index by URL."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    if idx.remove_page(url):
        click.echo(f"Removed: {url}")
    else:
        click.echo(f"Page not found: {url}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--config", default="config.yaml", help="Config file path")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--format", "fmt", default=None, type=click.Choice(["json", "text"]), help="Output format")
@click.pass_context
def status(ctx, config, data_dir, as_json, fmt):
    """Show system status: index size, interests, pipeline config."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    output_format = fmt or ("json" if as_json else "text")

    store = get_interest_store(dd)
    interests = store.list_all()
    idx = get_search_index(dd)
    count = idx.get_page_count()

    # Pipeline config
    from personal_index.config.pipeline_config import load_pipeline_config
    pipeline_enabled = False
    pipeline_steps = []
    try:
        pcfg = load_pipeline_config(config)
        pipeline_enabled = pcfg.enabled
        pipeline_steps = pcfg.get_enabled_steps()
    except Exception:
        pass

    if output_format == "json":
        status_data = {
            "data_dir": dd,
            "data_dir_exists": os.path.exists(dd),
            "interests_count": len(interests),
            "indexed_pages": count,
            "pipeline_enabled": pipeline_enabled,
            "pipeline_steps": pipeline_steps,
        }
        click.echo(json.dumps(status_data, indent=2))
    else:
        click.echo("Personal Index Status")
        click.echo("=" * 40)
        click.echo(f"Data dir: {dd}")
        click.echo(f"  Exists: {os.path.exists(dd)}")
        if os.path.exists(dd):
            size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, fn in os.walk(dd)
                for f in fn
            )
            click.echo(f"  Size: {size:,} bytes")
        click.echo(f"Interests: {len(interests)}")
        for interest in interests[:5]:
            click.echo(f"  - {interest.name} (priority={interest.priority})")
        if len(interests) > 5:
            click.echo(f"  ... and {len(interests) - 5} more")
        click.echo(f"Indexed pages: {count}")
        click.echo(f"Pipeline enabled: {pipeline_enabled}")
        click.echo(f"Pipeline steps: {', '.join(pipeline_steps)}")


@main.command()
@click.argument("url")
@click.option("-o", "--output", default=None, help="Save page content to file")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def fetch(ctx, url, output, data_dir):
    """Fetch a single URL and display its content."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scraper import Scraper

    scraper = Scraper()
    try:
        page = scraper.fetch(url)
        if output:
            with open(output, "w") as f:
                f.write(page.content or "")
            click.echo(f"Saved content to {output}")
        else:
            click.echo(f"Title: {page.title}")
            click.echo(f"URL: {page.url}")
            click.echo(f"Content length: {len(page.content or '')} chars")
            if page.content:
                click.echo(f"\n{page.content[:500]}")
    except Exception as e:
        click.echo(f"Fetch error: {e}", err=True)


@main.group()
def schedule():
    """Manage crawl schedules."""


@schedule.command("add")
@click.option("-n", "--name", required=True, help="Schedule name")
@click.option("-u", "--url", required=True, help="URL to crawl")
@click.option("-i", "--interval", default="daily", type=click.Choice(["hourly", "daily", "weekly"]), help="Crawl interval")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def add_schedule(ctx, name, url, interval, data_dir):
    """Add a crawl schedule."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    scheduler = Scheduler(data_dir=dd)
    scheduler.add(name, url, interval=interval)
    click.echo(f"Added schedule: {name} ({interval})")


@schedule.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def list_schedules(ctx, data_dir):
    """List all crawl schedules."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    scheduler = Scheduler(data_dir=dd)
    schedules = scheduler.list_all()
    if not schedules:
        click.echo("No schedules configured.")
        return
    for s in schedules:
        click.echo(f"  {s.name}: {s.url} ({s.interval})")


@schedule.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def remove_schedule(ctx, name, data_dir):
    """Remove a crawl schedule."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    scheduler = Scheduler(data_dir=dd)
    if scheduler.remove(name):
        click.echo(f"Removed schedule: {name}")
    else:
        click.echo(f"Schedule not found: {name}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def run_scheduler(ctx, data_dir):
    """Run the scheduler once (manual trigger)."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    scheduler = Scheduler(data_dir=dd)
    click.echo("Running scheduler...")
    try:
        scheduler.run_once()
        click.echo("Scheduler run complete.")
    except Exception as e:
        click.echo(f"Scheduler error: {e}", err=True)


@main.command()
@click.argument("path", nargs=-1, required=True)
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directory")
@click.option("--config", default="config.yaml", help="Config file path")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--tag", default=None, help="Tag to apply to imported files")
@click.pass_context
def import_cmd(ctx, path, recursive, config, data_dir, tag):
    """Import local files into the index.

    PATH can be a file or directory. Use --recursive for directories.
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from pathlib import Path

    from personal_index.content_extractor import ContentExtractor
    from personal_index.models import CrawledPage

    extractor = ContentExtractor()
    index = get_search_index(dd)
    imported = 0

    paths_to_import = []
    for path_arg in path:
        p = Path(path_arg)
        if p.is_file():
            paths_to_import.append(p)
        elif p.is_dir():
            if recursive:
                paths_to_import.extend(sorted(p.rglob("*")))
                paths_to_import = [f for f in paths_to_import if f.is_file()]
            else:
                paths_to_import.extend(sorted(p.glob("*")))
                paths_to_import = [f for f in paths_to_import if f.is_file()]

    for file_path in paths_to_import:
        try:
            with open(file_path, "r", errors="replace") as f:
                text = f.read()
            page = CrawledPage(
                url=f"file://{file_path.resolve()}",
                title=file_path.name,
                content=text,
            )
            index.add_page(page)
            imported += 1
        except Exception as e:
            click.echo(f"  Error importing {file_path}: {e}", err=True)

    click.echo(f"Imported {imported} file(s) into index.")


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
            if getattr(r, "snippet", ""):
                lines.append(f"{getattr(r, "snippet", "")}")
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
    """Manage content tags."""


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
    """Remove a tag."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.tags import TagStore
    store = TagStore(store_path=f"{dd}/tags.json")
    store.delete_tag(name)
    click.echo(f"Removed tag: {name}")


main.add_command(pipeline_cmd, name="pipeline")

if __name__ == "__main__":
    main()
