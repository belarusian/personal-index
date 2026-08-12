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


# ── init ──────────────────────────────────────────────────────────────
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--config", default=None, help="Config file path")
@click.pass_context
def init(ctx, data_dir, config):
    """Initialize a new personal-index data directory.

    Creates the data directory structure and default configuration.

    Examples:
        personal-index init
        personal-index init --data-dir ./my_index
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)
    for subdir in ["cache", "archive", "backups"]:
        os.makedirs(os.path.join(dd, subdir), exist_ok=True)

    # Use config path from option or default
    config_path = config if config else "config.yaml"
    
    # Create default config if not exists
    if not os.path.exists(config_path):
        default_config = {
            "data_dir": dd,
            "crawler": {
                "max_depth": 3,
                "max_pages_per_domain": 100,
                "timeout": 30,
                "politeness_delay": 1.0,
            },
            "pipeline": {
                "min_score_threshold": 0.0,
                "min_content_length": 100,
            },
        }
        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)

    click.echo(f"Initialized personal-index in '{dd}'")
    click.echo(f"Config written to '{config_path}'")


# ── interests ─────────────────────────────────────────────────────────
@main.group()
def interests():
    """Manage your content interests."""
    pass


@interests.command("add")
@click.option("--name", "-n", required=True, help="Interest name")
@click.option("--keyword", "-k", "keywords", multiple=True, help="Keywords to match")
@click.option("--priority", "-p", default=5, type=int, help="Priority (1-10)")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_add(ctx, name, keywords, priority, data_dir):
    """Add a new interest to track.

    Examples:
        personal-index interests add -n python -k python -k django
        personal-index interests add -n web -k javascript -k react -p 8
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    from personal_index.models import Interest
    interest = Interest(name=name, keywords=list(keywords), priority=priority)
    store.add(interest)
    click.echo(f"Added interest: {name}")


@interests.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_list(ctx, data_dir):
    """List all configured interests.

    Examples:
        personal-index interests list
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    all_interests = store.list_all()
    if not all_interests:
        click.echo("No interests configured.")
        return
    click.echo("Configured Interests:")
    click.echo("-" * 50)
    for interest in all_interests:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  {interest.name} [{status}] (priority: {interest.priority})")
        if interest.keywords:
            click.echo(f"    Keywords: {', '.join(interest.keywords)}")


@interests.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_remove(ctx, name, data_dir):
    """Remove an interest by name.

    Examples:
        personal-index interests remove python
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)
    if store.remove(name):
        click.echo(f"Removed interest '{name}'")
    else:
        click.echo(f"Interest '{name}' not found")


# ── tags ──────────────────────────────────────────────────────────────
@main.group()
def tags():
    """Manage content tags."""
    pass


@tags.command("add")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_add(ctx, tag_name, url, data_dir):
    """Add a tag to a page.

    Examples:
        personal-index tags add important https://example.com/page1
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    store.add_tag_to_page(url, tag_name)
    click.echo(f"Added tag '{tag_name}' to {url}")


@tags.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_list(ctx, data_dir):
    """List all tags.

    Examples:
        personal-index tags list
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    all_tags = store.list_tags()
    if not all_tags:
        click.echo("No tags configured.")
        return
    click.echo("Tags:")
    click.echo("-" * 40)
    for tag in all_tags:
        pages = store.get_pages_for_tag(tag.name)
        click.echo(f"  {tag.name} ({len(pages)} pages)")

@tags.command("remove")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_remove(ctx, tag_name, url, data_dir):
    """Remove a tag from a page.

    Examples:
        personal-index tags remove important https://example.com/page1
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    if store.remove_tag_from_page(url, tag_name):
        click.echo(f"Removed tag '{tag_name}' from {url}")
    else:
        click.echo(f"Tag '{tag_name}' not found on {url}")


# ── import ────────────────────────────────────────────────────────────
@main.command("import")
@click.argument("path")
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directory")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def import_cmd(ctx, path, recursive, data_dir):
    """Import local files or directories into the index.

    Reads text files and adds them to the search index.

    Examples:
        personal-index import ./article.txt
        personal-index import ./docs --recursive
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    index = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    imported = 0
    files = _collect_files(path, recursive)

    for filepath in files:
        try:
            with open(filepath, "r", errors="replace") as f:
                content = f.read()
        except OSError:
            continue

        if len(content.strip()) < 10:
            continue

        from personal_index.models import CrawledPage
        page = CrawledPage(
            url=f"file://{os.path.abspath(filepath)}",
            title=os.path.basename(filepath),
            content=content,
        )

        # Score and tag
        text = f"{page.title} {page.content}"
        matches = interest_store.matches_any(text, page.url)
        for interest in matches:
            tag_store.add_tag_to_page(page.url, interest.name)
            if not page.matched_interests:
                page.matched_interests = []
            page.matched_interests.append(interest.name)
        page.relevance_score = interest_store.total_score(text)

        index.add_page(page)
        imported += 1

    click.echo(f"Import complete: {imported} file(s) imported")


def _collect_files(path: str, recursive: bool) -> list[str]:
    """Collect files from a path."""
    path = os.path.abspath(path)
    if os.path.isfile(path):
        return [path]
    if os.path.isdir(path) and recursive:
        files = []
        for root, dirs, filenames in os.walk(path):
            for fn in filenames:
                fp = os.path.join(root, fn)
                if fn.endswith((".txt", ".md", ".html", ".htm", ".rst")):
                    files.append(fp)
        return files
    if os.path.isdir(path):
        files = []
        for fn in os.listdir(path):
            fp = os.path.join(path, fn)
            if os.path.isfile(fp) and fn.endswith((".txt", ".md", ".html", ".htm", ".rst")):
                files.append(fp)
        return files
    return []


# ── search ────────────────────────────────────────────────────────────
@main.command()
@click.argument("query")
@click.option("--limit", "-l", default=20, type=int, help="Maximum results")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json", "csv"]), help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def search(ctx, query, limit, tag, fmt, data_dir):
    """Search the indexed content.

    Performs full-text search across all indexed pages.

    Examples:
        personal-index search "python tutorial"
        personal-index search "web development" --limit 10
        personal-index search "api" --tag documentation
        personal-index search "rust" --format json
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = get_search_index(dd)

    if index.get_page_count() == 0:
        click.echo("No indexed content found. Run 'personal-index import' or 'personal-index pipeline' first.")
        return

    results = index.search(query, limit=limit)

    if tag:
        tag_store = get_tag_store(dd)
        tagged_urls = tag_store.get_pages_for_tag(tag)
        results = [r for r in results if r.url in tagged_urls]

    if fmt == "json":
        _output_search_json(results)
    elif fmt == "csv":
        _output_search_csv(results)
    else:
        _output_search_text(results, query)


def _output_search_text(results, query):
    """Output search results in text format."""
    if not results:
        click.echo(f"No results found for '{query}'")
        return
    click.echo(f"\nSearch results for '{query}' ({len(results)} found):")
    click.echo("-" * 60)
    for i, result in enumerate(results, 1):
        click.echo(f"\n{i}. {result.title}")
        click.echo(f"   {result.url}")
        click.echo(f"   Score: {result.relevance_score:.4f}")
        if result.snippet:
            click.echo(f"   {result.snippet[:200]}")


def _output_search_json(results):
    """Output search results in JSON format."""
    data = {
        "results": [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "relevance_score": r.relevance_score,
            }
            for r in results
        ],
        "total": len(results),
    }
    click.echo(json.dumps(data, indent=2))


def _output_search_csv(results):
    """Output search results in CSV format."""
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["rank", "title", "url", "score", "snippet"])
    for i, r in enumerate(results, 1):
        writer.writerow([i, r.title, r.url, f"{r.relevance_score:.4f}", r.snippet[:200]])
    click.echo(output.getvalue().strip())


# ── export ────────────────────────────────────────────────────────────
@main.command()
@click.option("--format", "fmt", default="markdown",
              type=click.Choice(["markdown", "json", "csv"]), help="Export format")
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
    index = get_search_index(dd)
    tag_store = get_tag_store(dd)
    pages = index.list_pages()

    if not pages:
        click.echo("No indexed content to export.")
        return

    if fmt == "markdown":
        content = _export_markdown(pages, tag_store)
    elif fmt == "json":
        content = _export_json(pages, tag_store)
    elif fmt == "csv":
        content = _export_csv(pages, tag_store)
    else:
        content = _export_markdown(pages, tag_store)

    if output:
        with open(output, "w") as f:
            f.write(content)
        click.echo(f"Exported {len(pages)} pages to '{output}'")
    else:
        click.echo(content)


def _export_markdown(pages, tag_store):
    """Export pages as markdown."""
    lines = ["# Search Results", ""]
    for i, page in enumerate(pages, 1):
        lines.append(f"## {i}. {page.title}")
        lines.append(f"- **URL**: {page.url}")
        lines.append(f"- **Score**: {page.score:.4f}")
        tags = tag_store.get_tags_for_page(page.url)
        if tags:
            lines.append(f"- **Tags**: {', '.join(t.name for t in tags)}")
        snippet = page.content[:200] if page.content else ""
        if snippet:
            lines.append(f"\n{snippet}...")
        lines.append("")
    return "\n".join(lines)


def _export_json(pages, tag_store):
    """Export pages as JSON."""
    data = {
        "pages": [
            {
                "url": page.url,
                "title": page.title,
                "score": page.score,
                "tags": [t.name for t in tag_store.get_tags_for_page(page.url)],
                "snippet": (page.content or "")[:200],
            }
            for page in pages
        ],
        "total": len(pages),
    }
    return json.dumps(data, indent=2)


def _export_csv(pages, tag_store):
    """Export pages as CSV."""
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["rank", "title", "url", "score", "tags", "snippet"])
    for i, page in enumerate(pages, 1):
        tags = [t.name for t in tag_store.get_tags_for_page(page.url)]
        writer.writerow([
            i, page.title, page.url, f"{page.score:.4f}",
            "; ".join(tags), (page.content or "")[:200]
        ])
    return output.getvalue().strip()


# ── status ────────────────────────────────────────────────────────────
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def status(ctx, data_dir):
    """Show status of your personal-index.

    Displays counts of indexed pages, interests, tags, and storage usage.

    Examples:
        personal-index status
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    page_count = idx.get_page_count()
    tag_count = tag_store.get_tag_count()
    interests = interest_store.list_all()
    interest_count = len(interests)

    total_size = 0
    if os.path.exists(dd):
        for dirpath, dirnames, filenames in os.walk(dd):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"  Indexed pages:  {page_count}")
    click.echo(f"  Interests:      {interest_count}")
    click.echo(f"  Tags:           {tag_count}")
    click.echo(f"  Tagged pages:   {tag_store.get_tagged_page_count()}")

    if interests:
        click.echo("")
        click.echo("Interests:")
        for interest in interests:
            click.echo(f"  - {interest.name}: {', '.join(interest.keywords[:5])}")

    if total_size > 0:
        if total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        click.echo(f"\nStorage: {size_str}")


# ── crawl ─────────────────────────────────────────────────────────────
@main.command()
@click.argument("url", required=False)
@click.option("--depth", "-d", default=3, type=int, help="Max crawl depth")
@click.option("--max-pages", "-m", default=100, type=int, help="Max pages to crawl")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def crawl(ctx, url, depth, max_pages, data_dir):
    """Crawl a URL and extract content.

    Crawls a website starting from the given URL.

    Examples:
        personal-index crawl https://example.com
        personal-index crawl https://example.com -d 2 -m 50
    """
    if not url:
        click.echo("Error: URL is required")
        click.echo("Usage: personal-index crawl <url>")
        sys.exit(1)

    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    from personal_index.crawler.main import Crawler, CrawlerConfig
    from personal_index.interests import InterestStore

    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    crawler = Crawler(
        config=CrawlerConfig(
            max_depth=depth,
            max_pages=max_pages,
            delay=0.0,
            timeout=10,
        ),
        interest_store=interest_store,
    )

    try:
        pages = crawler.crawl([url])
        click.echo(f"Crawled {len(pages)} page(s) from {url}")
        for page in pages[:10]:
            click.echo(f"  - {page.title} ({page.url})")
        if len(pages) > 10:
            click.echo(f"  ... and {len(pages) - 10} more")
    finally:
        crawler.close()


# ── pipeline ──────────────────────────────────────────────────────────
@main.command()
@click.argument("urls", nargs=-1)
@click.option("--import-file", "-i", "import_files", multiple=True,
              help="Import local files instead of crawling")
@click.option("--depth", "-d", default=3, type=int, help="Max crawl depth")
@click.option("--max-pages", "-m", default=100, type=int, help="Max pages to crawl")
@click.option("--min-score", default=0.0, type=float, help="Minimum score threshold")
@click.option("--min-content-length", "-l", default=10, type=int,
              help="Minimum content length to include")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--steps", "-s", default=None,
              help="Comma-separated list of steps to run")
@click.option("--no-crawl", is_flag=True, help="Skip crawl stage")
@click.option("--no-filter", is_flag=True, help="Skip filter stage")
@click.option("--no-score", is_flag=True, help="Skip score stage")
@click.option("--no-tag", is_flag=True, help="Skip tag stage")
@click.option("--no-index", is_flag=True, help="Skip index stage")
@click.pass_context
def pipeline(ctx, urls, import_files, depth, max_pages, min_score,
             min_content_length, data_dir, steps, no_crawl, no_filter,
             no_score, no_tag, no_index):
    """Run the full content pipeline.

    Processes content through all stages: crawl -> extract -> filter ->
    score -> tag -> index. Can work with URLs (web crawling) or local
    files (import mode).

    Examples:
        personal-index pipeline https://example.com
        personal-index pipeline --import-file ./article.txt
        personal-index pipeline https://example.com -d 2 -m 50
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    from personal_index.config.pipeline_config import PipelineConfig
    from personal_index.pipeline_runner import PipelineRunner

    config = PipelineConfig(
        min_score_threshold=min_score,
        min_content_length=min_content_length,
        max_pages=max_pages,
        max_depth=depth,
    )

    runner = PipelineRunner(
        data_dir=dd,
        pipeline_config=config,
    )

    try:
        if import_files:
            click.echo(f"Imported {len(import_files)} file(s)")
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

        final_stats = runner.get_stats()
        click.echo("\nIndex stats:")
        click.echo(f"  Total indexed pages: {final_stats['indexed_pages']}")
        click.echo(f"  Total interests:     {final_stats['total_interests']}")
        click.echo(f"  Total tags:          {final_stats['total_tags']}")
        click.echo(f"  Tagged pages:        {final_stats['tagged_pages']}")

    finally:
        runner.close()


# ── stats (legacy alias for status) ───────────────────────────────────
@main.command()
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]),
              help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def stats(ctx, data_dir, fmt):
    """Show statistics about your personal-index.

    Displays counts of indexed pages, interests, tags, and storage usage.

    Examples:
        personal-index stats
        personal-index stats --format json
    """
    import json
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    page_count = idx.get_page_count()
    tag_count = tag_store.get_tag_count()
    interests = interest_store.list_all()
    interest_count = len(interests)

    total_size = 0
    if os.path.exists(dd):
        for dirpath, dirnames, filenames in os.walk(dd):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass

    if fmt == "json":
        data = {
            "indexed_pages": page_count,
            "total_interests": interest_count,
            "total_tags": tag_count,
            "tagged_pages": tag_store.get_tagged_page_count(),
        }
        if total_size > 0:
            data["storage_bytes"] = total_size
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo("Personal Index Statistics")
        click.echo("=" * 40)
        click.echo("  Indexed pages:  {}".format(page_count))
        click.echo("  Interests:      {}".format(interest_count))
        click.echo("  Tags:           {}".format(tag_count))
        click.echo("  Tagged pages:   {}".format(tag_store.get_tagged_page_count()))

        if interests:
            click.echo("")
            click.echo("Interests:")
            for interest in interests:
                click.echo("  - {}: {}".format(interest.name, ", ".join(interest.keywords[:5])))

        if total_size > 0:
            if total_size < 1024 * 1024:
                size_str = "{:.1f} KB".format(total_size / 1024)
            else:
                size_str = "{:.1f} MB".format(total_size / (1024 * 1024))
            click.echo("")
            click.echo("Storage: {}".format(size_str))


# ── list (legacy - list indexed pages) ────────────────────────────────
@main.command("list")
@click.option("--limit", "-l", default=20, type=int, help="Maximum pages to show")
@click.option("--sort", "-s", default="score", type=click.Choice(["score", "date", "title"]),
              help="Sort order")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json", "csv"]),
              help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def list_pages(ctx, limit, sort, data_dir, fmt):
    """List all indexed pages.

    Shows all pages currently in the search index.

    Examples:
        personal-index list
        personal-index list --limit 50
        personal-index list --sort date
        personal-index list --format json
    """
    import csv
    import io
    import json
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)

    pages = idx.list_pages()
    if sort == "date":
        pages = sorted(pages, key=lambda p: p.crawled_at or "", reverse=True)
    elif sort == "title":
        pages = sorted(pages, key=lambda p: p.title.lower())
    else:
        pages = sorted(pages, key=lambda p: p.score, reverse=True)
    pages = pages[:limit]

    if not pages:
        if fmt == "json":
            click.echo(json.dumps({"pages": [], "total": 0}, indent=2))
        else:
            click.echo("No indexed pages found. Run 'personal-index pipeline' to add content.")
        return

    if fmt == "json":
        data = {
            "pages": [
                {
                    "url": p.url,
                    "title": p.title,
                    "score": p.score,
                    "crawled_at": p.crawled_at,
                    "content_length": p.content_length,
                }
                for p in pages
            ],
            "total": len(pages),
        }
        click.echo(json.dumps(data, indent=2))
    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["rank", "title", "url", "score", "crawled_at", "content_length"])
        for i, p in enumerate(pages, 1):
            writer.writerow([i, p.title, p.url, f"{p.score:.4f}", p.crawled_at or "", p.content_length])
        click.echo(output.getvalue().strip())
    else:
        click.echo("Indexed Pages")
        click.echo("=" * 60)
        for i, page in enumerate(pages, 1):
            click.echo("{}. {}".format(i, page.title))
            click.echo("   {}".format(page.url))
            click.echo("   Score: {:.4f}".format(page.score))
            click.echo("")


# ── doctor ────────────────────────────────────────────────────────────
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

    if not os.path.exists(dd):
        issues.append(f"Data directory '{dd}' does not exist. Run 'personal-index init'.")
    else:
        for subdir in ["cache", "archive", "backups"]:
            if not os.path.exists(os.path.join(dd, subdir)):
                warnings.append(f"Missing subdirectory: {subdir}")

    if not os.path.exists("config.yaml"):
        warnings.append("No config.yaml found. Run 'personal-index init' for defaults.")

    idx = get_search_index(dd)
    if idx.get_page_count() == 0:
        warnings.append("Index is empty. Run 'personal-index pipeline' to add content.")

    interest_store = get_interest_store(dd)
    if not interest_store.list_all():
        warnings.append("No interests configured. Add interests for better scoring.")

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



# ── schedule ──────────────────────────────────────────────────────────
@main.group()
def schedule():
    """Manage scheduled crawling jobs."""
    pass


@schedule.command("add")
@click.option("--name", "-n", required=True, help="Job name")
@click.option("--url", "-u", "urls", multiple=True, help="Seed URLs to crawl")
@click.option("--interval", "-i", default=24, type=int, help="Interval in hours")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_add(ctx, name, urls, interval, data_dir):
    """Add a scheduled crawl job.

    Examples:
        personal-index schedule add -n daily -u https://example.com -i 24
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleStore, ScheduleConfig, ScheduleEntry
    from datetime import datetime, timedelta, timezone
    
    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)
    
    config = ScheduleConfig(
        interval_hours=interval,
        seed_urls=list(urls),
    )
    
    entry = ScheduleEntry(
        name=name,
        config=config,
        next_run=datetime.now(timezone.utc) + timedelta(hours=interval),
    )
    
    store.add(entry)
    click.echo(f"Added scheduled job '{name}' to run every {interval} hours")


@schedule.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_list(ctx, data_dir):
    """List all scheduled jobs.

    Examples:
        personal-index schedule list
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store_path = os.path.join(dd, "schedules.json")
    
    if not os.path.exists(store_path):
        click.echo("No scheduled jobs found.")
        return
    
    from personal_index.scheduler import ScheduleStore
    store = ScheduleStore(path=store_path)
    
    entries = list(store.list_all())
    if not entries:
        click.echo("No scheduled jobs found.")
        return
    
    click.echo("Scheduled Jobs:")
    click.echo("-" * 50)
    for entry in entries:
        status = "enabled" if entry.config.enabled else "disabled"
        next_run = entry.next_run.strftime("%Y-%m-%d %H:%M:%S") if entry.next_run else "N/A"
        click.echo(f"  {entry.name} [{status}]")
        click.echo(f"    Next run: {next_run}")
        click.echo(f"    Interval: {entry.config.interval_hours} hours")
        if entry.config.seed_urls:
            click.echo(f"    URLs: {', '.join(entry.config.seed_urls[:3])}")


@schedule.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_remove(ctx, name, data_dir):
    """Remove a scheduled job.

    Examples:
        personal-index schedule remove daily
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store_path = os.path.join(dd, "schedules.json")
    
    if not os.path.exists(store_path):
        click.echo("No scheduled jobs found.")
        return
    
    from personal_index.scheduler import ScheduleStore
    store = ScheduleStore(path=store_path)
    
    if store.remove(name):
        click.echo(f"Removed scheduled job '{name}'")
    else:
        click.echo(f"Scheduled job '{name}' not found")


# ── config ────────────────────────────────────────────────────────────
@main.group()
def config():
    """Manage personal-index configuration."""
    pass


@config.command("show")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_show(ctx, data_dir):
    """Show current configuration.

    Examples:
        personal-index config show
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    
    from personal_index.config.loader import load_config
    config = load_config("config.yaml")
    
    click.echo("Personal Index Configuration")
    click.echo("=" * 40)
    click.echo(f"Data directory: {config.data_dir}")
    click.echo("")
    click.echo("Crawler settings:")
    click.echo(f"  Max depth: {config.crawl.max_depth}")
    click.echo(f"  Max pages: {getattr(config.crawl, "max_pages_per_domain", getattr(config.crawl, "max_pages", "N/A"))}")
    click.echo(f"  Timeout: {config.crawl.timeout} seconds")
    click.echo(f"  Politeness delay: {config.crawl.politeness_delay} seconds")
    click.echo("")
    click.echo("Scheduler settings:")
    click.echo(f"  Enabled: {'Yes' if config.scheduler.enabled else 'No'}")
    click.echo(f"  Interval: {config.scheduler.interval_hours} hours")


@config.command("set-crawler")
@click.option("--max-depth", "-d", type=int, help="Max crawl depth")
@click.option("--max-pages", "-m", type=int, help="Max pages per domain")
@click.option("--timeout", "-t", type=int, help="Request timeout in seconds")
@click.option("--politeness-delay", "-p", type=float, help="Delay between requests")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_set_crawler(ctx, max_depth, max_pages, timeout, politeness_delay, data_dir):
    """Configure crawler settings.

    Examples:
        personal-index config set-crawler --max-depth 5
        personal-index config set-crawler -m 100 -t 60
    """
    from personal_index.config.loader import load_config, save_config
    
    config = load_config("config.yaml")
    
    if max_depth is not None:
        config.crawl.max_depth = max_depth
    if max_pages is not None:
        config.crawl.max_pages = max_pages
    if timeout is not None:
        config.crawl.timeout = timeout
    if politeness_delay is not None:
        config.crawl.politeness_delay = politeness_delay
    
    save_config(config, "config.yaml")
    click.echo("Crawler configuration updated")


@config.command("set-schedule")
@click.option("--interval", "-i", type=int, help="Default interval in hours")
@click.option("--enabled/--disabled", default=None, help="Enable or disable scheduler")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_set_schedule(ctx, interval, enabled, data_dir):
    """Configure scheduler settings.

    Examples:
        personal-index config set-schedule --interval 12
        personal-index config set-schedule --enabled
    """
    from personal_index.config.loader import load_config, save_config
    
    config = load_config("config.yaml")
    
    if interval is not None:
        config.scheduler.interval_hours = interval
    if enabled is not None:
        config.scheduler.enabled = enabled
    
    save_config(config, "config.yaml")
    click.echo("Scheduler configuration updated")



# ── top (show highest-scored pages) ───────────────────────────────────
@main.command()
@click.option("--limit", "-l", default=10, type=int, help="Number of top pages to show")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]),
              help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def top(ctx, limit, fmt, data_dir):
    """Show the highest-scored indexed pages.

    Displays pages ranked by their relevance score.

    Examples:
        personal-index top
        personal-index top --limit 20
        personal-index top --format json
    """
    import json
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    pages = idx.list_pages()[:limit]

    if not pages:
        click.echo("No indexed pages found. Run 'personal-index pipeline' first.")
        return

    if fmt == "json":
        data = {
            "top_pages": [
                {
                    "rank": i + 1,
                    "url": p.url,
                    "title": p.title,
                    "score": p.score,
                    "crawled_at": p.crawled_at,
                    "tags": [],
                }
                for i, p in enumerate(pages)
            ],
            "total": len(pages),
        }
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"
Top {len(pages)} pages by score:")
        click.echo("=" * 60)
        for i, p in enumerate(pages, 1):
            click.echo(f"
{i}. {p.title}")
            click.echo(f"   Score: {p.score:.4f}")
            click.echo(f"   URL:   {p.url}")
            click.echo(f"   Date:  {p.crawled_at or 'N/A'}")


# ── dedup (find and remove duplicates) ────────────────────────────────
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--method", "-m", default="all",
              type=click.Choice(["hash", "url", "similarity", "all"]),
              help="Deduplication method")
@click.option("--similarity-threshold", type=float, default=0.9,
              help="Similarity threshold (0.0-1.0)")
@click.option("--dry-run", is_flag=True, help="Show duplicates without removing")
@click.pass_context
def dedup(ctx, data_dir, method, similarity_threshold, dry_run):
    """Find and remove duplicate content.

    Analyzes indexed content for duplicates using hash matching,
    URL normalization, or similarity scoring.

    Examples:
        personal-index dedup
        personal-index dedup --method hash
        personal-index dedup --method similarity --similarity-threshold 0.8
        personal-index dedup --dry-run
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.content_dedup import ContentDeduplicator
    idx = get_search_index(dd)
    pages = idx.list_pages()
    if not pages:
        click.echo("No indexed content found.")
        return

    items = []
    for page in pages:
        items.append({
            "url": page.url,
            "title": page.title,
            "content": page.content or "",
        })

    dedup_obj = ContentDeduplicator(similarity_threshold=similarity_threshold)

    if method == "hash":
        result = dedup_obj.dedup_by_hash(items)
    elif method == "url":
        result = dedup_obj.dedup_by_url(items)
    elif method == "similarity":
        result = dedup_obj.dedup_by_similarity(items)
    else:
        result = dedup_obj.dedup_all(items)

    click.echo(result.summary())
    click.echo()

    if result.duplicate_groups:
        click.echo("Duplicate Groups:")
        click.echo("-" * 40)
        for group in result.duplicate_groups:
            click.echo(f"
  Representative: {group.representative}")
            click.echo(f"  Method: {group.dedup_method}")
            click.echo(f"  Score: {group.similarity_score:.2f}")
            for dup in group.duplicates:
                click.echo(f"    Duplicate: {dup}")

        if not dry_run:
            click.echo(f"
Removing {result.removed_count} duplicates...")
            urls_to_remove = set()
            for group in result.duplicate_groups:
                urls_to_remove.update(group.duplicates)
            removed = 0
            for url in urls_to_remove:
                if idx.remove_page(url):
                    removed += 1
            idx._save()
            click.echo(f"Removed {removed} duplicate pages.")
        else:
            click.echo("
(Dry run - no changes made)")
    else:
        click.echo("No duplicates found!")


# ── health (content health check) ─────────────────────────────────────
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--min-content-length", type=int, default=50, help="Minimum content length")
@click.option("--min-title-length", type=int, default=3, help="Minimum title length")
@click.option("--require-tags", is_flag=True, help="Require tags on all items")
@click.option("--min-score", type=float, default=0.0, help="Minimum score threshold")
@click.pass_context
def health(ctx, data_dir, min_content_length, min_title_length, require_tags, min_score):
    """Check the health of indexed content.

    Analyzes all indexed pages for quality issues including
    missing titles, short content, and bad status codes.

    Examples:
        personal-index health
        personal-index health --require-tags --min-score 5.0
        personal-index health --min-content-length 100
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.content_health import ContentHealthCheck, ContentHealthChecker
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    pages = idx.list_pages()
    if not pages:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    items = []
    for page in pages:
        page_tags = list(tag_store.get_tags_for_url(page.url))
        items.append({
            "url": page.url,
            "title": page.title,
            "content": page.content or "",
            "tags": page_tags,
            "score": page.score,
            "status_code": getattr(page, "status_code", 200),
        })

    config = ContentHealthCheck(
        min_content_length=min_content_length,
        min_title_length=min_title_length,
        require_tags=require_tags,
        require_score=min_score > 0,
        min_score=min_score,
    )
    checker = ContentHealthChecker(config=config)
    report = checker.check_all(items)

    click.echo(report.summary())
    click.echo()

    if report.total_issues > 0:
        click.echo(f"Issues Found ({report.total_issues}):")
        click.echo("-" * 40)
        for result in report.results:
            if result.issues:
                click.echo(f"
  {result.url}")
                for issue in result.issues:
                    click.echo(f"    [{issue.severity.value}] {issue.message}")
                    if issue.suggestion:
                        click.echo(f"       -> {issue.suggestion}")
    else:
        click.echo("All content is healthy!")


# ── recommend (content recommendations) ───────────────────────────────
@main.command()
@click.argument("query", required=False)
@click.option("--top-n", "-n", default=5, help="Number of recommendations")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--keyword-weight", default=0.6, help="Keyword overlap weight")
@click.option("--tag-weight", default=0.3, help="Tag similarity weight")
@click.option("--score-weight", default=0.1, help="Score weight")
@click.pass_context
def recommend(ctx, query, top_n, data_dir, keyword_weight, tag_weight, score_weight):
    """Get content recommendations based on a query or seed content.

    Analyzes indexed content and recommends related pages based on
    keyword overlap, tag similarity, and content scores.

    Examples:
        personal-index recommend "python tutorial"
        personal-index recommend "python tutorial" --top-n 10
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.content_recommender import ContentItem, Recommender
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    recommender = Recommender(min_score=0.0)
    pages = idx.list_pages()
    for page in pages:
        page_tags = list(tag_store.get_tags_for_url(page.url))
        item = ContentItem(
            url=page.url,
            title=page.title,
            content=page.content or "",
            keywords=getattr(page, "keywords", []) or [],
            tags=page_tags,
            score=page.score,
        )
        recommender.add_item(item)

    if not recommender.item_count:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    if query:
        recs = recommender.recommend_for_keywords(query.split(), top_n=top_n)
    else:
        recs = recommender.recommend_for_keywords([], top_n=top_n)

    if not recs:
        click.echo("No recommendations found.")
        return

    click.echo(f"Top {top_n} Recommendations:")
    click.echo("=" * 50)
    for i, rec in enumerate(recs, 1):
        click.echo(f"
{i}. {rec.title}")
        click.echo(f"   URL: {rec.url}")
        click.echo(f"   Score: {rec.score:.3f}")
        click.echo(f"   Reason: {rec.reason}")


# ── verify (pipeline verification) ────────────────────────────────────
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--quick", "-q", is_flag=True, help="Quick verification (skip full pipeline test)")
@click.pass_context
def verify(ctx, data_dir, quick):
    """Verify that the personal-index pipeline works end-to-end.

    Runs a self-test that creates temporary content and processes it
    through all pipeline stages to verify everything is working.

    Examples:
        personal-index verify
        personal-index verify --quick
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    click.echo("Verifying personal-index pipeline...")
    click.echo("=" * 50)

    errors = []
    checks_passed = 0
    checks_total = 0

    def check(name, condition, detail=""):
        nonlocal checks_passed, checks_total
        checks_total += 1
        if condition:
            checks_passed += 1
            click.echo(f"  ✓ {name}")
        else:
            errors.append(f"✗ {name}: {detail}")
            click.echo(f"  ✗ {name}: {detail}")

    # Check 1: Data directory writable
    test_file = os.path.join(dd, ".verify_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        check("Data directory is writable", True)
    except OSError as e:
        check("Data directory is writable", False, str(e))

    # Check 2: Interest store works
    try:
        from personal_index.interests import InterestStore
        from personal_index.models import Interest
        interest_store = InterestStore(store_path=os.path.join(dd, "verify_interests.json"))
        interest_store.add(Interest(name="verify_test", keywords=["verify"]))
        interests = interest_store.list_all()
        check("Interest store works", len(interests) > 0, "Could not store interests")
        interest_store._interests.clear()
        interest_store._save()
    except (RuntimeError, OSError, ValueError) as e:
        check("Interest store works", False, str(e))

    # Check 3: Tag store works
    try:
        tag_store = TagStore(store_path=os.path.join(dd, "verify_tags.json"))
        tag_store.add_tag_to_page("http://test.com", "verify")
        tags = tag_store.get_tags_for_page("http://test.com")
        check("Tag store works", any(t.name == "verify" for t in tags), "Could not store tags")
        tag_store._page_tags.clear()
        tag_store._save()
    except (RuntimeError, OSError, ValueError) as e:
        check("Tag store works", False, str(e))

    # Check 4: Search index works
    try:
        from personal_index.models import CrawledPage
        search_index = SearchIndex(db_path=os.path.join(dd, "verify_index.json"))
        test_page = CrawledPage(
            url="http://verify.test/page1",
            title="Verify Test Page",
            content="This is a verification test page for the pipeline.",
        )
        search_index.add_page(test_page)
        results = search_index.search("verification")
        check("Search index works", len(results) > 0, "Could not search index")
        search_index.remove_page("http://verify.test/page1")
        search_index._save()
    except (RuntimeError, OSError, ValueError) as e:
        check("Search index works", False, str(e))

    # Check 5: Content filter works
    try:
        from personal_index.content_filter import ContentFilter, FilterConfig
        content_filter = ContentFilter(config=FilterConfig(min_content_length=10))
        test_page = CrawledPage(
            url="http://test.com",
            title="Test",
            content="This is test content for verification.",
        )
        included = content_filter.should_include(test_page)
        check("Content filter works", included, "Filter rejected valid content")
    except (RuntimeError, OSError, ValueError) as e:
        check("Content filter works", False, str(e))

    # Check 6: Content scorer works
    try:
        from personal_index.content_scoring import ContentScorer, ScoreWeights
        scorer = ContentScorer(weights=ScoreWeights())
        score = scorer.score(
            keyword_matches=1,
            total_keywords=2,
            word_count=10,
            domain_authority=0.5,
        )
        check("Content scorer works", score.total >= 0, "Scorer returned invalid score")
    except (RuntimeError, OSError, ValueError) as e:
        check("Content scorer works", False, str(e))

    # Full pipeline test (skip with --quick)
    if not quick:
        click.echo("
Running full pipeline self-test...")
        try:
            test_data_dir = os.path.join(dd, ".verify_pipeline")
            os.makedirs(test_data_dir, exist_ok=True)

            test_file_path = os.path.join(test_data_dir, "test_article.txt")
            with open(test_file_path, "w") as f:
                f.write(
                    "Python is a versatile programming language used for web development, "
                    "data science, and machine learning. Python has a clean and readable syntax "
                    "that makes it popular among beginners and experts alike."
                )

            mini_interest_store = InterestStore(store_path=os.path.join(test_data_dir, "interests.json"))
            mini_interest_store.add(Interest(name="python", keywords=["python", "programming"]))

            mini_tag_store = TagStore(store_path=os.path.join(test_data_dir, "tags.json"))
            mini_search_index = SearchIndex(db_path=os.path.join(test_data_dir, "search_index.json"))
            mini_filter = ContentFilter(
                config=FilterConfig(min_content_length=10),
                interest_store=mini_interest_store,
            )
            mini_scorer = ContentScorer(weights=ScoreWeights())

            with open(test_file_path, "r") as f:
                content = f.read()
            page = CrawledPage(
                url=test_file_path,
                title="Python Overview",
                content=content,
            )

            if not mini_filter.should_include(page):
                check("Full pipeline: filter stage", False, "Content was filtered out")
            else:
                score = mini_scorer.score(
                    keyword_matches=2,
                    total_keywords=2,
                    word_count=len(content.split()),
                    domain_authority=0.5,
                )
                page.relevance_score = score.total

                mini_tag_store.add_tag_to_page(page.url, "python")
                mini_tag_store.add_tag_to_page(page.url, "programming")

                mini_search_index.add_page(page)

                results = mini_search_index.search("python")

                check("Full pipeline: all stages", len(results) > 0,
                      "Pipeline did not produce searchable results")

            import shutil
            shutil.rmtree(test_data_dir, ignore_errors=True)

        except (RuntimeError, OSError, ValueError) as e:
            check("Full pipeline: all stages", False, str(e))

    # Cleanup verify files
    for f in ["verify_interests.json", "verify_tags.json", "verify_index.json"]:
        path = os.path.join(dd, f)
        if os.path.exists(path):
            os.remove(path)

    # Summary
    click.echo(f"
{'=' * 50}")
    click.echo(f"Results: {checks_passed}/{checks_total} checks passed")

    if errors:
        click.echo(f"
Failed checks ({len(errors)}):")
        for error in errors:
            click.echo(f"  {error}")
        sys.exit(1)
    else:
        click.echo("
✓ All checks passed! Your pipeline is working correctly.")


# ── watch (watch directory for changes) ───────────────────────────────
@main.command()
@click.argument("path")
@click.option("--interval", "-i", default=30, type=int, help="Check interval in seconds")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--recursive", "-r", is_flag=True, help="Watch directories recursively")
@click.option("--once", "-o", is_flag=True, help="Run once and exit (no continuous monitoring)")
@click.pass_context
def watch(ctx, path, interval, data_dir, recursive, once):
    """Watch a directory for changes and re-index automatically.

    Monitors a directory for new or modified files and automatically
    runs the pipeline on changes.

    Examples:
        personal-index watch ./docs
        personal-index watch ./content --interval 60 --recursive
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    if not os.path.exists(path):
        click.echo(f"Error: Path '{path}' does not exist.", err=True)
        sys.exit(1)

    click.echo(f"Watching {path} for changes (interval: {interval}s)")
    if once:
        click.echo("Running once and exiting.")
    else:
        click.echo("Press Ctrl+C to stop.")

    import time
    file_times = {}

    def scan_files(target_path):
        times = {}
        if os.path.isfile(target_path):
            times[target_path] = os.path.getmtime(target_path)
        elif os.path.isdir(target_path):
            for root, dirs, files in os.walk(target_path):
                for f in files:
                    fp = os.path.join(root, f)
                    if fp.endswith((".txt", ".md", ".html", ".htm", ".json", ".xml", ".rst")):
                        times[fp] = os.path.getmtime(fp)
        return times

    try:
        while True:
            current_times = scan_files(path)
            new_files = []
            modified_files = []

            for fp, mtime in current_times.items():
                if fp not in file_times:
                    new_files.append(fp)
                elif mtime > file_times[fp]:
                    modified_files.append(fp)

            if new_files or modified_files:
                click.echo(f"
[{time.strftime('%H:%M:%S')}] Changes detected:")
                for f in new_files:
                    click.echo(f"  + {f}")
                for f in modified_files:
                    click.echo(f"  ~ {f}")

                changed = new_files + modified_files
                if changed:
                    click.echo(f"
Re-indexing {len(changed)} file(s)...")
                    from click.testing import CliRunner
                    from personal_index.cli_pipeline_unified import run_pipeline
                    runner = CliRunner()
                    import_args = ["--data-dir", dd]
                    for f in changed:
                        import_args.extend(["--import-file", f])
                    result = runner.invoke(run_pipeline, import_args)
                    if result.exit_code != 0:
                        click.echo(f"  Warning: Pipeline had issues: {result.output}", err=True)
                    else:
                        click.echo("  Re-index complete.")

            file_times = current_times

            if once:
                click.echo("
Watch completed (single run mode).")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("
Watch stopped.")


if __name__ == "__main__":
    main()
