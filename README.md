# personal-index

A personal web search engine that scans, filters, and indexes the web based on your interests.

## Features

1. **Interest Configuration** - Define topics, keywords, and URL patterns to track
2. **Web Crawler** - Configurable depth, politeness, and rate limiting
3. **Local Search Index** - Full-text search with relevance scoring
4. **Content Filtering** - Only store what matches your interests
5. **CLI Interface** - Add interests, run crawls, search, view results
6. **Scheduled Crawling** - Periodic re-scanning of tracked topics

## Installation

    pip install -e .[dev]

## Usage

    # Add an interest
    personal-index interest add --topic "machine learning" --keywords "AI, neural networks, deep learning"

    # Run a crawl
    personal-index crawl --depth 2 --rate-limit 1.0

    # Search the index
    personal-index search "neural networks"

    # View results
    personal-index results --query "neural networks" --limit 10

## License

MIT
