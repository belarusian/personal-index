# personal-index

A personal web search engine where you define your interests and the system scans, filters, and indexes the web for you.

## Features

- Interest Configuration - Define topics, keywords, and URL patterns to track
- Web Crawler - Configurable depth, politeness, and rate limiting
- Local Search Index - Full-text search with relevance scoring
- Content Filtering - Only store what matches your interests
- CLI Interface - Add interests, run crawls, search, view results
- Scheduled Crawling - Periodic re-scanning of tracked topics

## Installation

    pip install -e .

## Usage

    personal-index interest add --topic "machine learning" --keywords "AI, neural networks"
    personal-index crawl --depth 3 --rate-limit 1
    personal-index search "neural networks"
    personal-index results --limit 10

## License

MIT
