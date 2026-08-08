"""CLI interface for personal-index search engine."""

import argparse
import json
import sys
from typing import List, Optional


def format_search_result(result, idx: int) -> str:
    """Format a search result for display."""
    lines = [
        f"  {idx}. [{result.score:.4f}] {result.document.title or result.document.url}",
        f"     URL: {result.document.url}",
    ]
    if result.matched_terms:
        lines.append(f"     Matched: {', '.join(result.matched_terms)}")
    snippet = result.document.content[:200] if result.document.content else ""
    if snippet:
        lines.append(f"     {snippet}...")
    return "\n".join(lines)


def cmd_add_interest(args) -> int:
    """Handle 'add-interest' command."""
    from personal_index.interests import Interest, InterestManager

    manager = InterestManager()

    interest = Interest(
        name=args.name,
        keywords=args.keywords or [],
        url_patterns=args.url_patterns or [],
        topics=args.topics or [],
    )
    try:
        manager.add_interest(interest)
        print(f"Added interest: {interest.name}")
        if interest.keywords:
            print(f"  Keywords: {', '.join(interest.keywords)}")
        if interest.url_patterns:
            print(f"  URL patterns: {', '.join(interest.url_patterns)}")
        if interest.topics:
            print(f"  Topics: {', '.join(interest.topics)}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list_interests(args) -> int:
    """Handle 'list-interests' command."""
    from personal_index.interests import InterestManager

    manager = InterestManager()
    interests = manager.list_interests()
    if not interests:
        print("No interests configured.")
        return 0

    print(f"Configured interests ({len(interests)}):")
    for interest in interests:
        print(f"\n  [{interest.name}]")
        if interest.keywords:
            print(f"    Keywords: {', '.join(interest.keywords)}")
        if interest.url_patterns:
            print(f"    URL patterns: {', '.join(interest.url_patterns)}")
        if interest.topics:
            print(f"    Topics: {', '.join(interest.topics)}")
    return 0


def cmd_remove_interest(args) -> int:
    """Handle 'remove-interest' command."""
    from personal_index.interests import InterestManager

    manager = InterestManager()
    interest = manager.get_interest(args.name)
    if interest:
        manager.remove_interest(args.name)
        print(f"Removed interest: {args.name}")
        return 0
    else:
        print(f"Interest not found: {args.name}", file=sys.stderr)
        return 1


def cmd_search(args) -> int:
    """Handle 'search' command."""
    from personal_index.index import SearchIndex

    index = SearchIndex()
    results = index.search(args.query, limit=args.limit)

    if not results:
        print(f"No results found for: {args.query}")
        return 0

    print(f"Search results for '{args.query}' ({len(results)} found):")
    print()
    for i, result in enumerate(results, 1):
        print(format_search_result(result, i))
        print()
    return 0


def cmd_crawl(args) -> int:
    """Handle 'crawl' command."""
    from personal_index.crawler import CrawlConfig, WebCrawler

    config = CrawlConfig(
        max_depth=args.depth,
        politeness_delay=args.delay,
        rate_limit=args.rate_limit,
        max_pages=args.max_pages,
        allowed_domains=args.domains or [],
    )
    crawler = WebCrawler(config)
    results = crawler.crawl(args.url)

    stats = crawler.get_stats()
    print(f"Crawl complete:")
    print(f"  Pages crawled: {stats['total_crawled']}")
    print(f"  Unique hosts: {stats['unique_hosts']}")
    return 0


def cmd_stats(args) -> int:
    """Handle 'stats' command."""
    from personal_index.index import SearchIndex

    index = SearchIndex()
    stats = index.get_stats()
    print("Index Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total terms: {stats['total_terms']}")
    print(f"  URLs indexed: {stats['total_urls_indexed']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="personal-index",
        description="Personal web search engine - track your interests and search locally",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # add-interest command
    add_parser = subparsers.add_parser("add-interest", help="Add a new interest to track")
    add_parser.add_argument("--name", "-n", required=True, help="Interest name")
    add_parser.add_argument("--keywords", "-k", nargs="+", help="Keywords to match")
    add_parser.add_argument("--url-patterns", "-u", nargs="+", help="URL patterns to match")
    add_parser.add_argument("--topics", "-t", nargs="+", help="Topics to track")
    add_parser.set_defaults(func=cmd_add_interest)

    # list-interests command
    list_parser = subparsers.add_parser("list-interests", help="List all configured interests")
    list_parser.set_defaults(func=cmd_list_interests)

    # remove-interest command
    rm_parser = subparsers.add_parser("remove-interest", help="Remove an interest")
    rm_parser.add_argument("name", help="Interest name to remove")
    rm_parser.set_defaults(func=cmd_remove_interest)

    # search command
    search_parser = subparsers.add_parser("search", help="Search the local index")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results")
    search_parser.set_defaults(func=cmd_search)

    # crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Crawl URLs")
    crawl_parser.add_argument("url", help="Starting URL")
    crawl_parser.add_argument("--depth", "-d", type=int, default=3, help="Max crawl depth")
    crawl_parser.add_argument("--delay", type=float, default=1.0, help="Politeness delay (seconds)")
    crawl_parser.add_argument("--rate-limit", type=int, default=10, help="Requests per minute")
    crawl_parser.add_argument("--max-pages", type=int, default=1000, help="Max pages to crawl")
    crawl_parser.add_argument("--domains", nargs="+", help="Allowed domains")
    crawl_parser.set_defaults(func=cmd_crawl)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.set_defaults(func=cmd_stats)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
