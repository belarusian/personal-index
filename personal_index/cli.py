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
import sys
from typing import Any

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
            "filter": {
                "min_content_length": 100,
                "min_title_length": 3,
                "blocked_domains": [],
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
        sys.exit(1)


# ── tags ──────────────────────────────────────────────────────────────
@main.group()
def tags():
    """Manage content tags."""


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

def _score_and_tag_page(
    page: Any, text: str, tag_store: Any, interest_store: Any
) -> None:
    """Score a page against interests and apply matching tags."""
    matches = interest_store.matches_any(text, page.url)
    for interest in matches:
        tag_store.add_tag_to_page(page.url, interest.name)
        if not page.matched_interests:
            page.matched_interests = []
        page.matched_interests.append(interest.name)
    page.relevance_score = interest_store.total_score(text)


def _import_single_file(filepath: str) -> Any | None:
    """Read and parse a single file into a CrawledPage."""
    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read()
    except OSError:
        return None
    if len(content.strip()) < 10:
        return None
    from personal_index.models import CrawledPage
    return CrawledPage(
        url=f"file://{os.path.abspath(filepath)}",
        title=os.path.basename(filepath),
        content=content,
    )


@main.command("import")
@click.argument("path")
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directory")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def import_cmd(ctx, path, recursive, data_dir):
    """Import local files or directories into the index."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    if not os.path.exists(path):
        click.echo(f"Error: '{path}' not found", err=True)
        sys.exit(1)

    index = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    imported = 0
    for filepath in _collect_files(path, recursive):
        page = _import_single_file(filepath)
        if page is None:
            continue
        text = f"{page.title} {page.content}"
        _score_and_tag_page(page, text, tag_store, interest_store)
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
@click.option("--limit", "-n", "-l", default=20, type=int, help="Maximum results")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json", "csv"]), help="Output format")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def search(ctx, query, limit, tag, fmt, as_json, data_dir):
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

    if as_json or fmt == "json":
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
    data = [
        {
            "url": r.url,
            "title": r.title,
            "snippet": r.snippet,
            "relevance_score": r.relevance_score,
        }
        for r in results
    ]
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
    """Show status of your personal-index."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    page_count = idx.get_page_count()
    tag_count = tag_store.get_tag_count()
    interests = interest_store.list_all()
    storage_bytes = _compute_storage_bytes(dd)

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"  Pages indexed:  {page_count}")
    click.echo(f"  Interests:      {len(interests)}")
    click.echo(f"  Tags:           {tag_count}")
    click.echo(f"  Tagged pages:   {tag_store.get_tagged_page_count()}")

    if interests:
        _print_interests(interests)

    if storage_bytes > 0:
        click.echo(f"\nStorage: {_format_storage_size(storage_bytes)}")


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

def _expand_import_files(import_files: list[str], recursive: bool) -> list[str]:
    """Expand import file paths, walking directories recursively if requested.

    Args:
        import_files: List of file or directory paths.
        recursive: If True, walk directories for supported extensions.

    Returns:
        Flattened list of file paths.
    """
    expanded_files = []
    for f in import_files:
        if os.path.isdir(f) and recursive:
            for root, dirs, files in os.walk(f):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    if filepath.endswith(('.txt', '.md', '.html', '.htm', '.json', '.xml', '.rst')):
                        expanded_files.append(filepath)
        else:
            expanded_files.append(f)
    return expanded_files


def _print_pipeline_stats(stats) -> None:  # type: ignore[no-untyped-def]
    """Print pipeline run statistics to stdout."""
    click.echo(f"\nPipeline complete in {stats.elapsed_seconds:.1f}s:")
    click.echo(f"  Crawled:      {stats.pages_crawled}")
    click.echo(f"  Extracted:    {stats.pages_extracted}")
    click.echo(f"  Filtered in:  {stats.pages_filtered_in}")
    click.echo(f"  Filtered out: {stats.pages_filtered_out}")
    click.echo(f"  Scored:       {stats.pages_scored}")
    click.echo(f"  Tagged:       {stats.pages_tagged}")
    click.echo(f"  Tags applied: {stats.tags_applied}")
    click.echo(f"  Indexed:      {stats.pages_indexed}")
    click.echo(f"  Errors:       {len(stats.errors)}")
    if stats.errors:
        for err in stats.errors[:5]:
            click.echo(f"    - {err}")


def _print_index_stats(data_dir: str) -> None:
    """Print index statistics (pages, interests, tags) to stdout."""
    idx = get_search_index(data_dir)
    tag_store = get_tag_store(data_dir)
    interest_store = get_interest_store(data_dir)
    click.echo("\nIndex stats:")
    click.echo(f"  Total indexed pages: {idx.get_page_count()}")
    click.echo(f"  Total interests:     {len(interest_store.list_all())}")
    click.echo(f"  Total tags:          {tag_store.get_tag_count()}")
    click.echo(f"  Tagged pages:        {tag_store.get_tagged_page_count()}")


def _create_pipeline_runner(data_dir: str, depth: int, max_pages: int,
                            min_score: float, min_content_length: int):
    """Create configured PipelineRunner instance."""
    from personal_index.config.pipeline_config import PipelineConfig
    from personal_index.pipeline_runner import PipelineRunner
    config = PipelineConfig(
        min_score_threshold=min_score,
        min_content_length=min_content_length,
        max_pages=max_pages,
        max_depth=depth,
    )
    return PipelineRunner(data_dir=data_dir, pipeline_config=config)


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
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directories")
@click.pass_context
def pipeline(ctx, urls, import_files, depth, max_pages, min_score,
             min_content_length, data_dir, steps, no_crawl, no_filter,
             no_score, no_tag, no_index, recursive):
    """Run the full content pipeline."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    runner = _create_pipeline_runner(dd, depth, max_pages, min_score, min_content_length)

    try:
        if import_files:
            expanded = _expand_import_files(import_files, recursive)
            click.echo(f"Imported: {len(expanded)} file(s)")
            stats = runner.run_from_files(expanded)
        elif urls:
            click.echo(f"Running pipeline on {len(urls)} URL(s)...")
            stats = runner.run(list(urls))
        else:
            click.echo("No URLs or files specified.")
            sys.exit(1)

        _print_pipeline_stats(stats)
        _print_index_stats(dd)
    finally:
        runner.close()


# ── stats (legacy alias for status) ───────────────────────────────────

def _compute_storage_bytes(data_dir: str) -> int:
    """Compute total storage bytes used by the data directory."""
    total_size = 0
    if os.path.exists(data_dir):
        for dirpath, dirnames, filenames in os.walk(data_dir):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
    return total_size


def _format_stats_text(page_count: int, interest_count: int, tag_count: int,
                      tagged_count: int, interests: list, storage_bytes: int) -> None:
    """Format and print statistics in text format."""
    click.echo("Personal Index Statistics")
    click.echo("=" * 40)
    click.echo(f"  indexed_pages:  {page_count}")
    click.echo(f"  interests:      {interest_count}")
    click.echo(f"  tags:           {tag_count}")
    click.echo(f"  tagged_pages:   {tagged_count}")

    if interests:
        click.echo("")
        click.echo("Interests:")
        for interest in interests:
            click.echo("  - {}: {}".format(interest.name, ", ".join(interest.keywords[:5])))

    if storage_bytes > 0:
        if storage_bytes < 1024 * 1024:
            size_str = f"{storage_bytes / 1024:.1f} KB"
        else:
            size_str = f"{storage_bytes / (1024 * 1024):.1f} MB"
        click.echo("")
        click.echo(f"storage: {size_str}")


def _format_storage_size(total_size: int) -> str:
    """Format byte count to human-readable string."""
    if total_size < 1024 * 1024:
        return f"{total_size / 1024:.1f} KB"
    return f"{total_size / (1024 * 1024):.1f} MB"


def _print_interests(interests: list) -> None:
    """Print interest list to stdout."""
    click.echo("")
    click.echo("Interests:")
    for interest in interests:
        click.echo("  - {}: {}".format(interest.name, ", ".join(interest.keywords[:5])))


@main.command()
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def stats(ctx, output_format, data_dir):
    """Show statistics about your personal-index."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    page_count = idx.get_page_count()
    tag_count = tag_store.get_tag_count()
    interests = interest_store.list_all()
    storage_bytes = _compute_storage_bytes(dd)

    if output_format == "json":
        click.echo(json.dumps({
            "indexed_pages": page_count,
            "interests": len(interests),
            "total_tags": tag_count,
            "tagged_pages": tag_store.get_tagged_page_count(),
            "storage_bytes": storage_bytes,
        }, indent=2))
        return

    click.echo("Personal Index Statistics")
    click.echo("=" * 40)
    click.echo(f"  indexed_pages:  {page_count}")
    click.echo(f"  interests:      {len(interests)}")
    click.echo(f"  tags:           {tag_count}")
    click.echo(f"  tagged_pages:   {tag_store.get_tagged_page_count()}")

    if interests:
        _print_interests(interests)

    if storage_bytes > 0:
        click.echo(f"\nstorage: {_format_storage_size(storage_bytes)}")


def _sort_pages(pages: list, sort: str) -> list:
    """Sort pages by the specified criterion."""
    if sort == "date":
        return sorted(pages, key=lambda p: p.crawled_at or "", reverse=True)
    if sort == "title":
        return sorted(pages, key=lambda p: p.title.lower())
    return sorted(pages, key=lambda p: p.score, reverse=True)


def _format_pages_text(pages: list) -> None:
    """Print pages in text format."""
    click.echo("Indexed Pages")
    click.echo("=" * 60)
    for i, page in enumerate(pages, 1):
        click.echo(f"{i}. {page.title}")
        click.echo(f"   {page.url}")
        click.echo(f"   Score: {page.relevance_score:.4f}")
        click.echo("")


def _format_pages_csv(pages: list) -> None:
    """Print pages in CSV format."""
    import csv as _csv
    import io
    output = io.StringIO()
    writer = _csv.writer(output)
    writer.writerow(["title", "url", "score", "crawled_at"])
    for p in pages:
        writer.writerow([p.title, p.url, f"{p.score:.4f}", p.crawled_at])
    click.echo(output.getvalue().strip())


# ── list (legacy - list indexed pages) ────────────────────────────────
@main.command("list")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json", "csv"]), help="Output format")
@click.option("--limit", "-l", default=20, type=int, help="Maximum pages to show")
@click.option("--sort", "-s", default="score", type=click.Choice(["score", "date", "title"]),
              help="Sort order")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def list_pages(ctx, output_format, limit, sort, data_dir):
    """List all indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)

    pages = _sort_pages(idx.list_pages(), sort)[:limit]

    if not pages:
        if output_format == "json":
            click.echo(json.dumps({"pages": []}, indent=2))
        else:
            click.echo("No indexed pages found. Run 'personal-index pipeline' to add content.")
        return

    if output_format == "json":
        click.echo(json.dumps({"pages": [p.to_dict() for p in pages]}, indent=2, default=str))
    elif output_format == "csv":
        _format_pages_csv(pages)
    else:
        _format_pages_text(pages)


# ── top (show highest-scored pages) ──────────────────────────────────
@main.command()
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), help="Output format")
@click.option("--limit", "-l", default=10, type=int, help="Number of pages to show")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def top(ctx, output_format, limit, data_dir):
    """Show the highest-scored indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    pages = sorted(idx.list_pages(), key=lambda p: p.score, reverse=True)[:limit]

    if output_format == "json":
        click.echo(json.dumps({"top_pages": [p.to_dict() for p in pages]}, indent=2, default=str))
    else:
        click.echo(f"Top {len(pages)} pages by score:")
        click.echo("=" * 60)
        for i, p in enumerate(pages, 1):
            click.echo(f"{i}. {p.title}")
            click.echo(f"   Score: {p.score:.4f}")
            click.echo(f"   {p.url}")
            click.echo("")


# ── remove (remove page by URL) ──────────────────────────────────────
@main.command()
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def remove(ctx, url, data_dir):
    """Remove a page from the index by URL."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    pages = idx.list_pages()
    found = False
    for p in pages:
        if p.url == url:
            idx.remove_page(p.url)
            found = True
            break
    if not found:
        click.echo(f"Page not found: {url}")
        raise SystemExit(1)

    click.echo(json.dumps({"pages": [p.to_dict() for p in idx.list_pages()]}, indent=2, default=str))


# ── clear (clear index data) ─────────────────────────────────────────
@main.command()
@click.option("--index/--no-index", default=True, help="Clear search index")
@click.option("--tags/--no-tags", default=True, help="Clear tags")
@click.option("--interests/--no-interests", default=False, help="Clear interests")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def clear(ctx, index, tags, interests, data_dir):
    """Clear index data."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    if index:
        idx = get_search_index(dd)
        idx.clear()
        click.echo("Cleared search index")
    if tags:
        tag_store = get_tag_store(dd)
        tag_store.clear()
        click.echo("Cleared tags")
    if interests:
        interest_store = get_interest_store(dd)
        interest_store.clear()
        click.echo("Cleared interests")
    if not index and not tags and not interests:
        click.echo("Nothing to clear. Use --index, --tags, and/or --interests.")
    else:
        click.echo("Done.")


# ── doctor ────────────────────────────────────────────────────────────

def _doctor_check_data_dir(dd: str) -> tuple[list[str], list[str]]:
    """Check data directory existence and subdirectories.

    Returns:
        Tuple of (issues, warnings).
    """
    issues: list[str] = []
    warnings: list[str] = []
    if not os.path.exists(dd):
        issues.append(f"Data directory '{dd}' does not exist. Run 'personal-index init'.")
    else:
        for subdir in ["cache", "archive", "backups"]:
            if not os.path.exists(os.path.join(dd, subdir)):
                warnings.append(f"Missing subdirectory: {subdir}")
    return issues, warnings


def _doctor_check_config() -> list[str]:
    """Check for config.yaml existence."""
    if not os.path.exists("config.yaml"):
        return ["No config.yaml found. Run 'personal-index init' for defaults."]
    return []


def _doctor_check_index(dd: str) -> list[str]:
    """Check search index is populated."""
    idx = get_search_index(dd)
    if idx.get_page_count() == 0:
        return ["Index is empty. Run 'personal-index pipeline' to add content."]
    return []


def _doctor_check_interests(dd: str) -> list[str]:
    """Check interests are configured."""
    interest_store = get_interest_store(dd)
    if not interest_store.list_all():
        return ["No interests configured. Add interests for better scoring."]
    return []


def _doctor_print_results(issues: list[str], warnings: list[str], dd: str) -> None:
    """Print doctor diagnostic results."""
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

    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)
    click.echo(f"\nIndex: {idx.get_page_count()} pages")
    click.echo(f"Tags: {tag_store.get_tag_count()}")
    click.echo(f"Interests: {len(interest_store.list_all())}")


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
    issues: list[str] = []
    warnings: list[str] = []

    dir_issues, dir_warnings = _doctor_check_data_dir(dd)
    issues.extend(dir_issues)
    warnings.extend(dir_warnings)

    if not issues:
        warnings.extend(_doctor_check_config())
        warnings.extend(_doctor_check_index(dd))
        warnings.extend(_doctor_check_interests(dd))

    _doctor_print_results(issues, warnings, dd)

    if issues:
        sys.exit(1)



# ── schedule ──────────────────────────────────────────────────────────
@main.group()
def schedule():
    """Manage scheduled crawling jobs."""


@schedule.command("add")
@click.option("--name", "-n", required=True, help="Job name")
@click.option("--url", "-u", "urls", multiple=True, help="Seed URLs to crawl")
@click.option("--interval", "-i", default=24, type=int, help="Interval in hours")
@click.option("--depth", "-d", default=2, type=int, help="Crawl depth")
@click.option("--max-pages", "-m", default=50, type=int, help="Max pages per run")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_add(ctx, name, urls, interval, data_dir, depth, max_pages):
    """Add a scheduled crawl job.

    Examples:
        personal-index schedule add -n daily -u https://example.com -i 24
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from datetime import datetime, timedelta, timezone

    from personal_index.scheduler import ScheduleConfig, ScheduleEntry, ScheduleStore
    
    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)
    
    # Check for duplicates
    existing = store.list_all()
    if any(e.name == name for e in existing):
        click.echo(f"Scheduled job '{name}' already exists", err=True)
        sys.exit(1)
    
    config = ScheduleConfig(
        interval_hours=interval,
        seed_urls=list(urls),
        max_pages_per_run=max_pages,
        crawl_depth=depth,
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
        click.echo(f"Scheduled job '{name}' not found")
        sys.exit(1)
    
    from personal_index.scheduler import ScheduleStore
    store = ScheduleStore(path=store_path)
    
    if store.remove(name):
        click.echo(f"Removed scheduled job '{name}'")
    else:
        click.echo(f"Scheduled job '{name}' not found")
        sys.exit(1)


@schedule.command("run")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_run(ctx, name, data_dir):
    """Manually run a scheduled job now.

    Examples:
        personal-index schedule run daily
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store_path = os.path.join(dd, "schedules.json")

    if not os.path.exists(store_path):
        click.echo(f"Scheduled job '{name}' not found")
        sys.exit(1)

    from personal_index.scheduler import ScheduleStore
    store = ScheduleStore(path=store_path)

    entries = store.list_all()
    entry = next((e for e in entries if e.name == name), None)
    if not entry:
        click.echo(f"Scheduled job '{name}' not found")
        sys.exit(1)

    click.echo(f"Running scheduled job '{name}'...")
    click.echo(f"  URLs: {', '.join(entry.config.seed_urls)}")

    from personal_index.config.pipeline_config import PipelineConfig
    from personal_index.pipeline_runner import PipelineRunner
    config = PipelineConfig(
        max_depth=getattr(entry.config, 'crawl_depth', 2),
        max_pages=getattr(entry.config, 'max_pages_per_run', 50),
    )
    runner = PipelineRunner(data_dir=dd, pipeline_config=config)
    try:
        stats = runner.run(entry.config.seed_urls)
        click.echo(f"Job complete: {stats.pages_crawled} pages crawled")
    except Exception as e:  # noqa: BLE001
        click.echo(f"Job failed: {e}", err=True)
        sys.exit(1)
    finally:
        runner.close()


# ── config ────────────────────────────────────────────────────────────
@main.group()
def config():
    """Manage personal-index configuration."""


@config.command("show")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_show(ctx, data_dir):
    """Show current configuration.

    Examples:
        personal-index config show
    """
    data_dir or ctx.obj.get("data_dir", ".personal_index")
    
    from personal_index.config.loader import load_config
    config = load_config("config.yaml")
    
    click.echo("Personal Index Configuration")
    click.echo("=" * 40)
    click.echo(f"Data directory: {config.data_dir}")
    click.echo("")
    click.echo("Crawler settings:")
    click.echo(f"  Max depth: {config.crawl.max_depth}")
    max_pages = getattr(config.crawl, "max_pages_per_domain", getattr(config.crawl, "max_pages", "N/A"))
    click.echo(f"  Max pages: {max_pages}")
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
    from personal_index.models import CrawlConfig
    
    config = load_config(data_dir or ".personal_index")
    if not hasattr(config, 'crawl') or config.crawl is None:
        config.crawl = CrawlConfig()
    
    if max_depth is not None:
        config.crawl.max_depth = max_depth
    if max_pages is not None:
        config.crawl.max_pages_per_domain = max_pages
    if timeout is not None:
        config.crawl.timeout = timeout
    if politeness_delay is not None:
        config.crawl.politeness_delay = politeness_delay
    
    save_config(config, data_dir or ".personal_index")
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


# ── verify ────────────────────────────────────────────────────────────

def _verify_check_store(name: str, getter, attr: str, dd: str) -> tuple[bool, str]:
    """Verify a data store is accessible and readable.

    Args:
        name: Display name for the store.
        getter: Function to get the store instance.
        attr: Attribute/method to call on the store.
        dd: Data directory path.

    Returns:
        Tuple of (passed, message).
    """
    try:
        store = getter(dd)
        value = getattr(store, attr)()
        return True, f"{name}: {value} {'pages' if 'Search' in name else ''}"
    except Exception as e:  # noqa: BLE001
        return False, f"{name}: {e}"


def _verify_check_subdirs(dd: str) -> tuple[int, int]:
    """Check that expected subdirectories exist.

    Returns:
        Tuple of (passed, failed) counts.
    """
    passed = 0
    failed = 0
    for subdir in ["cache", "archive", "backups"]:
        if os.path.isdir(os.path.join(dd, subdir)):
            click.echo(f"  ✓ Directory: {subdir}/")
            passed += 1
        else:
            click.echo(f"  ✗ Directory: {subdir}/ missing")
            failed += 1
    return passed, failed


@main.command()
@click.option("--quick", is_flag=True, help="Quick verification only")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def verify(ctx, quick, data_dir):
    """Verify the integrity of your personal-index data.

    Checks that all data files are valid and consistent.

    Examples:
        personal-index verify
        personal-index verify --quick
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    checks_passed = 0
    checks_failed = 0

    store_checks = [
        ("Search index", get_search_index, "get_page_count"),
        ("Tag store", get_tag_store, "get_tag_count"),
        ("Interest store", get_interest_store, "list_all"),
    ]

    for name, getter, attr in store_checks:
        passed, msg = _verify_check_store(name, getter, attr, dd)
        if passed:
            click.echo(f"  ✓ {msg}")
            checks_passed += 1
        else:
            click.echo(f"  ✗ {msg}")
            checks_failed += 1

    if not quick:
        p, f = _verify_check_subdirs(dd)
        checks_passed += p
        checks_failed += f

    click.echo(f"All checks passed: {checks_passed}/{checks_passed + checks_failed}")


# ── watch ─────────────────────────────────────────────────────────────

def _index_file(fp: str, data_dir: str) -> None:
    """Read a single file and add it to the search index.

    Args:
        fp: File path to index.
        data_dir: Data directory for the search index.
    """
    with open(fp, "r", errors="replace") as f:
        content = f.read()
    if len(content.strip()) >= 10:
        from personal_index.models import CrawledPage
        page = CrawledPage(
            url=f"file://{os.path.abspath(fp)}",
            title=os.path.basename(fp),
            content=content,
        )
        idx = get_search_index(data_dir)
        idx.add_page(page)
        click.echo(f"  \u2713 Indexed: {fp}")


def _index_file_once(fp: str, data_dir: str) -> None:
    """Read and index a single file into the search index."""
    idx = get_search_index(data_dir)
    with open(fp, "r", errors="replace") as f:
        content = f.read()
    if len(content.strip()) < 10:
        return
    from personal_index.models import CrawledPage
    page = CrawledPage(
        url=f"file://{os.path.abspath(fp)}",
        title=os.path.basename(fp),
        content=content,
    )
    idx.add_page(page)
    click.echo(f"  ✓ Indexed: {fp}")


def _watch_once(paths: tuple[str, ...], data_dir: str) -> None:
    """Process paths in once mode — collect and index all files."""
    for path in paths:
        if os.path.isfile(path):
            click.echo(f"  Importing: {path}")
            files = _collect_files(path, False)
        elif os.path.isdir(path):
            files = _collect_files(path, True)
        else:
            continue
        for fp in files:
            try:
                _index_file_once(fp, data_dir)
            except Exception as e:  # noqa: BLE001
                click.echo(f"  ✗ Error: {e}", err=True)


def _validate_watch_paths(paths: tuple[str, ...]) -> None:
    """Validate that all watch paths exist."""
    if not paths:
        click.echo("Error: No paths specified to watch.", err=True)
        sys.exit(1)
    for path in paths:
        if not os.path.exists(path):
            click.echo(f"Error: '{path}' does not exist", err=True)
            sys.exit(1)


@main.command()
@click.argument("paths", nargs=-1)
@click.option("--interval", "-i", default=60, type=int, help="Check interval in seconds")
@click.option("--once", is_flag=True, help="Run once and exit")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def watch(ctx, paths, interval, once, data_dir):
    """Watch files or directories for changes and re-index."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)
    _validate_watch_paths(paths)

    click.echo(f"Watching {len(paths)} path(s) every {interval}s...")
    for path in paths:
        click.echo(f"  Watching: {path}")

    if once:
        _watch_once(paths, dd)
        click.echo("Watch complete (once mode)")
        return

    click.echo("Watch mode started. Press Ctrl+C to stop.")


# Register additional CLI commands from separate modules
from personal_index.cli_dedup import dedup
from personal_index.cli_health import health
from personal_index.cli_recommend import recommend

main.add_command(dedup)
main.add_command(health)
main.add_command(recommend)


if __name__ == "__main__":
    main()
