# Content Categorizer (`personal_index.content_categorizer`)

Status: **spec** — audited against current code (cycle 172).

Rule-based topic classifier. Analyzes content text, title, URL, and meta
description to assign topic categories with confidence scores. Uses keyword
matching across multiple signals (no ML).

## Module constants
- `BUILTIN_TOPICS: dict[str, list[str]]` — the built-in topic -> keyword-list
  map (technology, science, health, finance, education, business,
  entertainment, sports, travel, food, politics, environment). Loaded into the
  categorizer on construction.
- `ContentCategorizer.URL_TOPIC_HINTS: ClassVar[dict[str, list[str]]]` — topic
  name -> URL path/domain hint words (e.g. `"technology": ["tech", "dev",
  "api", ...]`).
- `ContentCategorizer.MIN_TOPIC_SCORE: float = 0.1` — **dead constant**:
  defined but never read anywhere in the module or repo (see contract holes).
  The actual threshold is the instance attr `self.min_score`.
- `ContentCategorizer.TITLE_BOOST: float = 2.0`, `URL_HINT_BOOST: float = 0.3`,
  `META_DESC_BOOST: float = 1.5` — signal multipliers used by `_score_topic`.

## TopicCategory (dataclass)
Fields: `name: str`, `keywords: list[str]` (default `[]`), `description: str`
(default `""`), `weight: float` (default `1.0`).
- `__post_init__` lower-cases every keyword in place
  (`self.keywords = [kw.lower() for kw in self.keywords]`).

## TopicScore (dataclass)
Fields: `topic: str`, `score: float`, `matched_keywords: list[str]` (default
`[]`), `signal_sources: list[str]` (default `[]`).
- `__lt__` / `__gt__` compare by `score` only (so the dataclass is orderable
  by score).

## CategorizationResult (dataclass)
Fields: `primary_topic: str`, `topics: list[TopicScore]` (default `[]`),
`confidence: float` (default `0.0`), `reasons: list[str]` (default `[]`),
`text_length: int` (default `0`), `keyword_count: int` (default `0`).
- `secondary_topics` (property) -> `self.topics[1:]` when there is more than
  one topic, else `[]` (i.e. everything after the primary).
- `top_n(n: int = 3) -> list[TopicScore]` -> `self.topics[:n]`, a NEW list
  (a slice) preserving score-descending order. `n=0` -> `[]`; `n >
  len(topics)` -> all topics. Does not mutate `self.topics`.

## ContentCategorizer
`ContentCategorizer(custom_topics: dict[str, list[str]] | None = None,
min_score: float = 0.1, max_topics: int = 5)`.
- Stores `self._topics` (dict name -> `TopicCategory`), `self._max_topics`,
  and `self.min_score`.
- Loads every `BUILTIN_TOPICS` entry as a `TopicCategory`, then adds each
  `custom_topics` entry via `add_topic`.

### Topic management
- `add_topic(name, keywords, description="", weight=1.0) -> TopicCategory` —
  lower-cases `name`, builds a `TopicCategory`, stores it under the
  lower-cased name, and returns it. **Overwrites** an existing topic of the
  same (case-insensitive) name.
- `remove_topic(name) -> bool` — lower-cases `name`; deletes and returns
  `True` if present, else returns `False` (no error).
- `get_topics() -> list[str]` — every stored topic name, sorted ascending
  (lexicographic); `[]` when empty.
- `get_topic(name) -> TopicCategory | None` — case-insensitive lookup
  (lower-cases `name`); `None` when absent.

### categorize(text, title="", url="", meta_description="") -> CategorizationResult
- **Guard path:** when `text`, `title`, and `meta_description` are ALL falsy,
  returns `CategorizationResult(primary_topic="unknown", topics=[],
  confidence=0.0, reasons=["no content provided"])` with `text_length` and
  `keyword_count` at their dataclass defaults (0).
- **Normal path:** tokenizes `text`/`title`/`meta_description` (lowercased,
  stopword-removed) into sets, lower-cases the raw signals, extracts URL hints
  from `url`, scores every topic via `_score_all_topics`, drops scores below
  `self.min_score`, caps the list at `self._max_topics`, then returns a
  `CategorizationResult` with:
  - `primary_topic` = top topic's name, or `"uncategorized"` when no topic
    clears the threshold.
  - `confidence` = top score rounded to 4 places.
  - `reasons` = the human-readable list from `_build_reasons`.
  - `text_length` = `len(text.split())`.
  - `keyword_count` = number of distinct text tokens (`len(tokens["text"])`).
- **Sentinel note:** the guard path uses `"unknown"` while the normal
  no-match path uses `"uncategorized"` — two distinct sentinels by design
  (documented in the docstring; not a divergence).

### categorize_batch(items: list[dict[str, str]]) -> list[CategorizationResult]
Maps `categorize` over each item, reading keys `text`, `title`, `url`,
`meta_description` (missing keys default to `""`). Returns one
`CategorizationResult` per item, in input order.

### Private helpers (contract-relevant)
- `_tokenize_signals(text, title, meta) -> dict[str, set]` — `{"text",
  "title", "meta"}` each a set of `tokenize(s, lowercase=True,
  remove_stopwords=True)`.
- `_lowercase_signals(text, title, meta) -> tuple[str, str, str]` — the three
  lower-cased raw strings (used for multi-word phrase matching).
- `_score_all_topics(...) -> list[TopicScore]` — scores every topic via
  `_score_topic`, keeps those with `score >= self.min_score` (score rounded to
  4 places), and returns them sorted by score descending.
- `_primary_and_confidence(topic_scores) -> tuple[str, float]` — top topic's
  `(name, score)`, or `("uncategorized", 0.0)` when the list is empty.
- `_score_topic(...) -> tuple[float, list[str], list[str]]` — sums weighted,
  capped contributions from up to four signals:
  - text: `min(len(matches) * 0.15, 1.0) * topic.weight`
  - title: `min(len(matches) * 0.3 * TITLE_BOOST, 1.0) * topic.weight`
  - meta: `min(len(matches) * 0.2 * META_DESC_BOOST, 1.0) * topic.weight`
  - URL hint: flat `URL_HINT_BOOST * topic.weight` when `topic.name in
    url_hints`.
  Returns `(0.0, [], [])` when no signal matches.
- `_match_keywords(keywords, tokens, raw_text) -> list[str]` — single-word
  keywords matched against the token set; multi-word keywords (containing a
  space) matched as substrings of the lower-cased `raw_text`.
- `_extract_url_hints(url) -> set` — `set()` when `url` is falsy; otherwise
  parses path + domain parts (lower-cased) and adds a topic name when any of
  its `URL_TOPIC_HINTS` words is a substring of a part. Falls back to
  `url.lower().split()` on a `ValueError` from `urlparse`.
- `_build_reasons(topic_scores, _text) -> list[str]` — `["no matching topics
  found in content"]` when empty; otherwise one line per top-3 topic of the
  form `"{topic} (score=..., signals=..., keywords=[...])"` (keyword preview
  capped at 5 with a `(+N more)` suffix).
- `_add_matches(matches, kw, src, source="text") -> list[str]` — appends each
  new match to `kw` (deduped, first-appearance order) and appends `source` to
  `src` only when `matches` is non-empty; returns the mutated `kw`.

## Contract holes
- `ContentCategorizer.MIN_TOPIC_SCORE` is a **dead class constant**: it is
  defined (line 269) but never read anywhere in the module or the repo. The
  real threshold is the instance attribute `self.min_score` (set from the
  `min_score` constructor arg, default `0.1`). A reader would reasonably
  assume `MIN_TOPIC_SCORE` is the threshold. -> **ARCH-7**.
