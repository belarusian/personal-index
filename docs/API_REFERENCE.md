# API Reference

## PipelineRunner

The main entry point for running the content pipeline.

### Constructor

```python
from personal_index.pipeline_runner import PipelineRunner, PipelineConfig

runner = PipelineRunner(
    data_dir=".personal_index",
    pipeline_config=PipelineConfig(
        max_depth=3,
        max_pages=100,
        min_content_length=100,
        min_score_threshold=0.0,
    ),
    progress_callback=my_callback,
)
```

### Methods

#### run(seed_urls) -> PipelineStats

Run the full pipeline on web URLs.

```python
stats = runner.run(["https://example.com"])
print(stats.summary())
```

#### run_from_files(file_paths) -> PipelineStats

Run the pipeline on local files.

```python
stats = runner.run_from_files(["./article.md", "./docs/"])
```

#### close()

Close the runner and persist all data.

## SearchIndex

In-memory search index with JSON persistence.

### Constructor

```python
from personal_index.index import SearchIndex

index = SearchIndex(db_path=".personal_index/search_index.json")
```

### Methods

#### add_page(page) -> int

Add a page to the index. Returns the new page count.

#### remove_page(url) -> bool

Remove a page by URL. Returns True if found and removed.

#### get_page(url) -> IndexedPage | None

Get a page by URL.

#### get_page_count() -> int

Get the total number of indexed pages.

#### list_pages() -> list[IndexedPage]

List all pages sorted by score (descending).

#### search(query, limit=10) -> list[SearchResult]

Search the index. Returns results sorted by relevance.

#### clear()

Remove all pages from the index.

#### close()

Save the index to disk.

## InterestStore

Persistent interest management.

### Constructor

```python
from personal_index.interests import InterestStore

store = InterestStore(store_path=".personal_index/interests.json")
```

### Methods

#### add(interest: Interest)

Add an interest.

#### remove(name: str) -> bool

Remove an interest by name.

#### get(name: str) -> Interest | None

Get an interest by name.

#### list_all() -> list[Interest]

List all interests.

#### matches(text: str, url: str = "") -> list[Interest]

Find interests matching text/URL.

## TagStore

Persistent tag management.

### Constructor

```python
from personal_index.tags import TagStore

store = TagStore(store_path=".personal_index/tags.json")
```

### Methods

#### add(tag: str, url: str)

Add a tag to a URL.

#### remove(tag: str, url: str) -> bool

Remove a tag from a URL.

#### list_all() -> dict[str, list[str]]

List all tags and their URLs.

#### get_tag_count() -> int

Get total number of unique tags.

## ContentFilter

Content quality and interest filtering.

### Constructor

```python
from personal_index.content_filter import ContentFilter, FilterConfig

config = FilterConfig(
    min_content_length=100,
    require_interest_match=False,
    blocked_domains=["spam.com"],
)
filter = ContentFilter(config=config, interest_store=store)
```

### Methods

#### should_include(page: CrawledPage) -> bool

Check if a page passes all filters.

#### get_filter_reasons(page: CrawledPage) -> list[str]

Get reasons why a page was filtered out.

## ContentScorer

Multi-factor content scoring.

### Constructor

```python
from personal_index.content_scoring import ContentScorer, ScoreWeights

weights = ScoreWeights(
    recency=0.2,
    relevance=0.25,
    engagement=0.15,
    quality=0.15,
    authority=0.1,
    freshness=0.15,
)
scorer = ContentScorer(weights=weights)
```

### Methods

#### score_page(content, title, url, interest_store) -> ContentScore

Score a page based on all configured factors.

## Data Models

### CrawledPage

```python
@dataclass
class CrawledPage:
    url: str
    title: str
    content: str | None
    status_code: int = 200
    content_length: int = 0
    keywords: list[str] = field(default_factory=list)
    matched_interests: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    crawled_at: str = ""
```

### IndexedPage

```python
@dataclass
class IndexedPage:
    url: str
    title: str
    content: str
    score: float = 0.0
    crawled_at: str = ""
    domain: str = ""
    status_code: int = 200
    content_length: int = 0
    language: str = "en"
    keywords: list[str] = field(default_factory=list)
    matched_interests: list[str] = field(default_factory=list)
```

### Interest

```python
@dataclass
class Interest:
    name: str
    interest_type: InterestType = InterestType.KEYWORD
    keywords: list[str] = field(default_factory=list)
    priority: int = 5
    enabled: bool = True
    match_mode: MatchMode = MatchMode.ANY
```

### SearchResult

```python
@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    relevance_score: float
```

### PipelineStats

```python
@dataclass
class PipelineStats:
    pages_crawled: int = 0
    pages_extracted: int = 0
    pages_filtered_in: int = 0
    pages_filtered_out: int = 0
    pages_scored: int = 0
    pages_tagged: int = 0
    pages_indexed: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    tags_applied: int = 0
    interests_matched: int = 0
```
