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

from personal_index.index import SearchIndex, SearchResult
from personal_index.tags import TagStore


def get_search_index(data_dir: str) -> SearchIndex:
    """Get or create a search index for the given data directory."""
    db_path = os.path.join(data_dir, "search_index.json")
    return SearchIndex(db_path=db_path)


def get_tag_store(data_dir: str) -> TagStore:
    """Get or create a tag store for the given data directory."""
    store_path = os.path.join(data_dir, "tags.json")
    return TagStore(store_path=store_path)


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

    config_path = config or "config.yaml"
    if not os.path.exists(config_path):
        default_config = {
            "data_dir": dd,
            "crawler": {
                "max_depth": 3,
                "politeness_delay": 1.0,
                "rate_limit": 10,
                "timeout": 30,
                "max_pages": 100,
            },
            "pipeline": {
                "enabled": True,
                "min_score_threshold": 0.0,
                "min_content_length": 100,
            },
            "scheduler": {
                "enabled": False,
                "interval_hours": 24,
            },
        }
        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        click.echo(f"Created {config_path}")
    else:
        click.echo(f"Config file already exists at {config_path}")

    # Create data directory structure
    for subdir in ["cache", "archive", "backups"]:
        os.makedirs(os.path.join(dd, subdir), exist_ok=True)

    click.echo(f"Initialized personal-index in {dd}")
    click.echo("Next steps:")
    click.echo("  1. Add interests: personal-index interests add mytopic -k keyword1 -k keyword2")
    click.echo("  2. Run pipeline: personal-index pipeline https://example.com")
    click.echo("  3. Search: personal-index search 'query'")


@main.command()
@click.argument("url", required=False)
@click.option("-d", "--depth", default=3, type=int, help="Max crawl depth")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--timeout", default=30, type=int, help="Request timeout in seconds")
@click.option("--delay", default=1.0, type=float, help="Delay between requests")
@click.option("--max-pages", default=100, type=int, help="Maximum pages to crawl")
@click.pass_context
def crawl(ctx, url, depth, data_dir, timeout, delay, max_pages):
    """Crawl a URL and its linked pages.

    Crawls the given URL and follows links up to the specified depth.
    Results are stored in the data directory for later processing.

    Examples:
        personal-index crawl https://example.com
        personal-index crawl https://example.com -d 2 --max-pages 50
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    if not url:
        click.echo("Error: URL is required for crawl command.", err=True)
        click.echo("Usage: personal-index crawl <URL>", err=True)
        sys.exit(1)

    from personal_index.crawler.main import Crawler, CrawlerConfig
    from personal_index.interests import InterestStore

    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    config = CrawlerConfig(
        max_depth=depth,
        delay=delay,
        timeout=timeout,
        max_pages=max_pages,
    )

    click.echo(f"Crawling {url} (depth={depth}, max_pages={max_pages})...")
    crawler = Crawler(config=config, interest_store=interest_store)
    try:
        pages = crawler.crawl([url], max_depth=depth)
        click.echo(f"Crawled {len(pages)} pages")

        # Save crawled pages
        pages_path = os.path.join(dd, "crawled_pages.json")
        pages_data = []
        for page in pages:
            pages_data.append({
                "url": page.url,
                "title": page.title,
                "content": page.content,
                "matched_interests": page.matched_interests or [],
            })
        with open(pages_path, "w") as f:
            json.dump(pages_data, f, indent=2)
        click.echo(f"Saved to {pages_path}")
    except (OSError, ValueError) as e:
        click.echo(f"Crawl error: {e}", err=True)
        sys.exit(1)
    finally:
        crawler.close()


@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=20, type=int, help="Max results")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.pass_context
def search(ctx, query, limit, tag, data_dir, format):
    """Search the indexed content.

    Searches through all indexed pages for the given query.
    Results are ranked by relevance score.

    Examples:
        personal-index search "python tutorial"
        personal-index search "javascript" --limit 10
        personal-index search "web development" --tag tutorial
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    if idx.get_page_count() == 0:
        click.echo("No indexed content found. Run 'personal-index pipeline <URL>' first.")
        return

    results = idx.search(query, limit=limit)

    if tag:
        tagged_urls = set(tag_store.get_pages_for_tag(tag))
        results = [r for r in results if r.url in tagged_urls]

    if not results:
        click.echo(f"No results found for '{query}'")
        return

    if format == "json":
        output = [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "score": r.relevance_score,
            }
            for r in results
        ]
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"Search results for '{query}' ({len(results)} found):")
        click.echo("-" * 60)
        for i, r in enumerate(results, 1):
            page_tags = tag_store.get_tags_for_page(r.url)
            tag_str = f" [{', '.join(t.name for t in page_tags)}]" if page_tags else ""
            click.echo(f"\n{i}. {r.title}{tag_str}")
            click.echo(f"   {r.url}")
            click.echo(f"   Score: {r.relevance_score:.4f}")
            if r.snippet:
                click.echo(f"   {r.snippet[:200]}")
            click.echo()


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def status(ctx, data_dir):
    """Show the current status of the index.

    Displays statistics about indexed pages, tags, and interests.

    Examples:
        personal-index status
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    from personal_index.interests import InterestStore
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"Data directory: {dd}")
    click.echo(f"Indexed pages: {idx.get_page_count()}")
    click.echo(f"Tags: {tag_store.get_tag_count()}")
    click.echo(f"Tagged pages: {tag_store.get_tagged_page_count()}")
    click.echo(f"Interests: {len(interest_store.list_all())}")

    # Show top tags
    tags = tag_store.list_tags()
    if tags:
        click.echo("\nTop tags:")
        for tag in sorted(tags, key=lambda t: len(tag_store.get_pages_for_tag(t.name)), reverse=True)[:10]:
            count = len(tag_store.get_pages_for_tag(tag.name))
            click.echo(f"  {tag.name}: {count} pages")


@main.group()
@click.pass_context
def interests(ctx):
    """Manage content interests.

    Interests define what content the pipeline should prioritize.
    Pages matching your interests get higher scores.

    Examples:
        personal-index interests list
        personal-index interests add programming -k python -k javascript
        personal-index interests remove programming
    """


@interests.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_list(ctx, data_dir):
    """List all configured interests."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.interests import InterestStore
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    all_interests = interest_store.list_all()

    if not all_interests:
        click.echo("No interests configured.")
        click.echo("Add one: personal-index interests add mytopic -k kw1 -k kw2")
        return

    click.echo(f"Configured interests ({len(all_interests)}):")
    for interest in all_interests:
        keywords = ", ".join(interest.keywords)
        click.echo(f"  {interest.name}: {keywords}")


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keyword", "keywords", multiple=True, required=True, help="Keywords (can specify multiple)")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_add(ctx, name, keywords, data_dir):
    """Add a new interest.

    NAME is the interest name (e.g., "programming", "news").
    KEYWORDS are terms to match (use -k multiple times).

    Examples:
        personal-index interests add programming -k python -k javascript -k web
        personal-index interests add science -k physics -k chemistry
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.interests import Interest, InterestStore
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    keyword_list = [k.strip() for k in keywords if k.strip()]
    interest = Interest(name=name, keywords=keyword_list)
    interest_store.add(interest)
    click.echo(f"Added interest: {name}")


@interests.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_remove(ctx, name, data_dir):
    """Remove an interest by name."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.interests import InterestStore
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    if interest_store.remove(name):
        click.echo(f"Removed interest: {name}")
    else:
        click.echo(f"Interest '{name}' not found", err=True)
        sys.exit(1)


@interests.command("priority")
@click.argument("name")
@click.argument("priority", type=int)
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_priority(ctx, name, priority, data_dir):
    """Set the priority of an interest (1-10)."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.interests import InterestStore
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    interest = interest_store.get(name)
    if interest:
        interest.priority = max(1, min(10, priority))
        interest_store.add(interest)
        click.echo(f"Set priority for '{name}' to {priority}")
    else:
        click.echo(f"Interest '{name}' not found", err=True)
        sys.exit(1)


@interests.command("enable")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_enable(ctx, name, data_dir):
    """Enable a disabled interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.interests import InterestStore
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    interest = interest_store.get(name)
    if interest:
        interest.enabled = True
        interest_store.add(interest)
        click.echo(f"Enabled interest: {name}")
    else:
        click.echo(f"Interest '{name}' not found", err=True)
        sys.exit(1)


@interests.command("disable")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_disable(ctx, name, data_dir):
    """Disable an interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.interests import InterestStore
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    interest = interest_store.get(name)
    if interest:
        interest.enabled = False
        interest_store.add(interest)
        click.echo(f"Disabled interest: {name}")
    else:
        click.echo(f"Interest '{name}' not found", err=True)
        sys.exit(1)


@main.group()
@click.pass_context
def tags(ctx):
    """Manage content tags.

    Tags are automatically assigned during the pipeline but can also
    be managed manually.

    Examples:
        personal-index tags list
        personal-index tags add my-tag https://example.com/page
    """


@main.group()
@click.pass_context
def tag(ctx):
    """Alias for 'tags' command (singular form)."""


@tags.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_list(ctx, data_dir):
    """List all tags and their page counts."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    tag_store = get_tag_store(dd)
    all_tags = tag_store.list_tags()

    if not all_tags:
        click.echo("No tags found.")
        return

    click.echo(f"Tags ({len(all_tags)}):")
    for tag in sorted(all_tags, key=lambda t: len(tag_store.get_pages_for_tag(t.name)), reverse=True):
        count = len(tag_store.get_pages_for_tag(tag.name))
        click.echo(f"  {tag.name}: {count} pages")


@tags.command("add")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_add(ctx, tag_name, url, data_dir):
    """Add a tag to a specific page URL."""
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
    """Remove a tag from a specific page URL."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    tag_store = get_tag_store(dd)
    if tag_store.remove_tag_from_page(url, tag_name):
        click.echo(f"Removed tag '{tag_name}' from {url}")
    else:
        click.echo(f"Tag '{tag_name}' not found on {url}", err=True)
        sys.exit(1)


# Tag aliases (singular form for backward compatibility)
@tag.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tag_list(ctx, data_dir):
    """Alias for tags list."""
    ctx.invoke(tags_list, data_dir=data_dir)


@tag.command("add")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tag_add(ctx, tag_name, url, data_dir):
    """Alias for tags add."""
    ctx.invoke(tags_add, tag_name=tag_name, url=url, data_dir=data_dir)


@tag.command("remove")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tag_remove(ctx, tag_name, url, data_dir):
    """Alias for tags remove."""
    ctx.invoke(tags_remove, tag_name=tag_name, url=url, data_dir=data_dir)


@main.command()
@click.option("--format", "-f", type=click.Choice(["markdown", "json", "csv"]), default="markdown", help="Export format")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--query", "-q", default=None, help="Filter by search query")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def export(ctx, format, output, query, data_dir):
    """Export indexed content to various formats.

    Examples:
        personal-index export --format markdown
        personal-index export -f json -o results.json
        personal-index export -q "python" -f csv
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    if query:
        results = idx.search(query, limit=100)
    else:
        results = []
        for url in idx._pages:
            page = idx._pages[url]
            snippet = idx._create_snippet(page.content, "")
            results.append(SearchResult(
                url=url,
                title=page.title,
                snippet=snippet,
                relevance_score=0.0,
            ))

    if format == "markdown":
        from personal_index.export_markdown import export_markdown
        output_text = export_markdown(results, tag_store)
    elif format == "json":
        from personal_index.content_export.json_export import export_json
        output_text = export_json(results, tag_store)
    elif format == "csv":
        from personal_index.content_export.csv_export import export_csv
        output_text = export_csv(results, tag_store)
    else:
        click.echo(f"Unsupported format: {format}", err=True)
        sys.exit(1)

    if output:
        with open(output, "w") as f:
            f.write(output_text)
        click.echo(f"Exported to {output}")
    else:
        click.echo(output_text)


@main.command(name="import")
@click.argument("filepaths", nargs=-1, required=True)
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--recursive", "-r", is_flag=True, help="Import directory recursively")
@click.pass_context
def import_content(ctx, filepaths, data_dir, recursive):
    """Import content from a file or directory.

    Import text files or JSON files into the index.
    Text files are imported as-is, JSON files are parsed as page data.

    Examples:
        personal-index import content.json
        personal-index import ./articles --recursive
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)

    imported = 0
    for filepath in filepaths:
        if not os.path.exists(filepath):
            click.echo(f"File not found: {filepath}", err=True)
            continue

        if os.path.isdir(filepath):
            if not recursive:
                click.echo(f"Is a directory: {filepath}. Use --recursive to import.", err=True)
                continue
            for root, dirs, files in os.walk(filepath):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    imported += _import_single_file(fpath, idx)
        else:
            imported += _import_single_file(filepath, idx)

    click.echo(f"Import complete: {imported} page(s) imported")


def _import_single_file(filepath: str, idx: SearchIndex) -> int:
    """Import a single file into the index. Returns number of pages imported."""
    from personal_index.models import CrawledPage

    if filepath.endswith(".json"):
        try:
            with open(filepath) as f:
                data = json.load(f)
            if isinstance(data, list):
                count = 0
                for item in data:
                    page = CrawledPage(
                        url=item.get("url", filepath),
                        title=item.get("title", os.path.basename(filepath)),
                        content=item.get("content", ""),
                    )
                    idx.add_page(page)
                    count += 1
                return count
            elif isinstance(data, dict):
                page = CrawledPage(
                    url=data.get("url", filepath),
                    title=data.get("title", os.path.basename(filepath)),
                    content=data.get("content", ""),
                )
                idx.add_page(page)
                return 1
            else:
                # Unknown JSON structure
                return 0
        except json.JSONDecodeError:
            click.echo(f"Invalid JSON in {filepath}")
            return 0
    else:
        # Text file - import as a single page
        try:
            with open(filepath, "r", errors="replace") as f:
                content = f.read()
            page = CrawledPage(
                url=filepath,
                title=os.path.basename(filepath),
                content=content,
            )
            idx.add_page(page)
            return 1
        except (OSError, ValueError) as e:
            click.echo(f"Error reading {filepath}: {e}")
            return 0
        return 0


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def reset(ctx, data_dir):
    """Reset the index, clearing all data.

    WARNING: This deletes all indexed content, tags, and cached data.
    Your config.yaml and interests are preserved.

    Examples:
        personal-index reset
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    files_to_remove = [
        os.path.join(dd, "search_index.json"),
        os.path.join(dd, "tags.json"),
        os.path.join(dd, "crawled_pages.json"),
    ]

    dirs_to_remove = [
        os.path.join(dd, "cache"),
        os.path.join(dd, "archive"),
    ]

    for f in files_to_remove:
        if os.path.exists(f):
            os.remove(f)
            click.echo(f"Removed {f}")

    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)
            click.echo(f"Removed {d}")

    click.echo("Index reset complete.")


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def validate(ctx, data_dir):
    """Validate the index data integrity.

    Checks for corrupted data files and consistency issues.

    Examples:
        personal-index validate
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    errors = []
    warnings = []

    # Check index consistency
    indexed_urls = set(idx._pages.keys())
    indexed_words = set(idx._word_index.keys())

    # Check for orphaned tags
    all_tagged_urls = set(tag_store._page_tags.keys())
    orphaned = all_tagged_urls - indexed_urls
    if orphaned:
        warnings.append(f"{len(orphaned)} tagged URLs not in index (orphaned tags)")

    # Check for missing tags
    if indexed_urls and not all_tagged_urls:
        warnings.append("No tags found for indexed pages")

    # Check index file
    if idx.db_path and os.path.exists(idx.db_path):
        try:
            with open(idx.db_path) as f:
                json.load(f)
        except json.JSONDecodeError:
            errors.append("Corrupted search index file")

    # Check tag file
    if tag_store.store_path and os.path.exists(tag_store.store_path):
        try:
            with open(tag_store.store_path) as f:
                json.load(f)
        except json.JSONDecodeError:
            errors.append("Corrupted tags file")

    click.echo("Validation Results")
    click.echo("=" * 40)
    click.echo(f"Indexed pages: {len(indexed_urls)}")
    click.echo(f"Indexed words: {len(indexed_words)}")
    click.echo(f"Tags: {tag_store.get_tag_count()}")
    click.echo(f"Tagged pages: {len(all_tagged_urls)}")

    if errors:
        click.echo(f"\nErrors ({len(errors)}):")
        for e in errors:
            click.echo(f"  ✗ {e}")
    else:
        click.echo("\n✓ No errors found")

    if warnings:
        click.echo(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            click.echo(f"  ⚠ {w}")

    if errors:
        sys.exit(1)


# Config management commands
@main.group()
@click.pass_context
def config(ctx):
    """Manage configuration settings.

    Examples:
        personal-index config show
        personal-index config set-crawler --max-depth 5
        personal-index config set-schedule --interval 12
    """


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


# Import pipeline command
from personal_index.cli_pipeline import pipeline

main.add_command(pipeline)

if __name__ == "__main__":
    main()
