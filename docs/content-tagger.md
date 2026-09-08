# Content Tagger (spec)

`personal_index.content_tagger` — the "tag" stage of the
crawl→filter→score→tag→index pipeline. Detects which topics a piece of text
belongs to by counting keyword occurrences, and emits one `Tag` per matched
topic with a confidence score.

The package exports three names (`__init__.py` `__all__`):
`ContentTagger`, `Tag`, `TopicDetector`.

## Public API

### `Tag` (dataclass)
`personal_index.content_tagger.tag`. A single detected topic with confidence.

Fields, in order:
- `name: str` — topic name (e.g. `"python"`).
- `confidence: float = 0.5` — detection confidence in `[0, 1]`.

Methods:
- `to_dict() -> dict[str, Any]` — `{"name": ..., "confidence": ...}`.
- `from_dict(data) -> Tag` (classmethod) — reads `data["name"]` (required,
  `KeyError` if absent) and `data.get("confidence", 0.5)`.
- `__eq__(other)` — `True` iff `other` is a `Tag` with equal `name` and
  `confidence`; returns `NotImplemented` for non-`Tag` operands.

### `TopicDetector`
`personal_index.content_tagger.detector`. The keyword-matching engine.

#### `DEFAULT_TOPICS` (ClassVar `dict[str, list[str]]`)
Twenty built-in topics (programming, python, web_development,
machine_learning, ai, data_science, devops, security, database, mobile,
design, testing, performance, version_control, blockchain, cloud_computing,
networking, operating_system, mathematics, education), each mapped to a list
of keywords. Note several keywords are shared across topics (e.g. `"cloud"`
in both devops and cloud_computing; `"statistics"` in data_science and
mathematics; `"firewall"` in security and networking; `"optimization"` in
performance and mathematics), so one text can match multiple topics.

#### `__init__(self)`
Copies `DEFAULT_TOPICS` into `self._topics` as `_TopicDefinition` objects
(name, keywords, `weight=1.0`).

#### `detect(self, text: str) -> list[Tag]`
**Guard path:** if `text` is falsy or whitespace-only, returns `[]`.

Otherwise:
1. Lowercases `text` once (`text_lower`).
2. For each registered topic, sums `len(re.findall(re.escape(kw_lower),
   text_lower))` across all of the topic's keywords (case-insensitive
   substring matching — see contract hole 1).
3. Emits a `Tag` for the topic iff that total `match_count > 0`. Each topic
   is emitted at most once.
4. Confidence = `round(min(0.5 + match_count * 0.1, 1.0), 2)`.
5. Returns the list sorted by confidence descending (ties keep the topic's
   insertion order, since `list.sort` is stable).

**Side effects:** none (pure query).

#### `add_topic(self, name: str, keywords: list[str], weight: float = 1.0)`
Adds or overwrites `self._topics[name]`. **Contract hole 2:** `weight` is
stored on the `_TopicDefinition` but `detect()` never reads it, so the
`weight` argument has no effect on confidence or emission.

#### `remove_topic(self, name: str)`
`self._topics.pop(name, None)` — no error if `name` is not registered.

#### `get_all_topics(self) -> list[str]`
Returns `list(self._topics.keys())` (insertion order; built-ins first, then
any `add_topic` additions).

### `TagResult` (dataclass)
`personal_index.content_tagger.tagger`. The return object of `ContentTagger`.

Fields, in order:
- `content: str` — the input text (echoed back verbatim).
- `tags: list[Tag] = []` — detected tags.

Methods:
- `to_dict() -> dict[str, Any]` — `{"content": ..., "tags": [t.to_dict() ...]}`.
- `from_dict(data) -> TagResult` (classmethod) — reads
  `data.get("content", "")` and maps `data.get("tags", [])` through
  `Tag.from_dict`.

### `ContentTagger`
`personal_index.content_tagger.tagger`. High-level interface wrapping a
`TopicDetector` plus per-tag usage statistics.

#### `__init__(self)`
Creates `self._detector = TopicDetector()` and `self._tag_stats: dict[str, int] = {}`.

#### `tag(self, content: str, min_confidence: float = 0.0) -> TagResult`
**Guard path:** if `content` is falsy or whitespace-only, returns
`TagResult(content=content, tags=[])` and updates no statistics.

Otherwise:
1. `tags = self._detector.detect(content)`.
2. Filters to `t.confidence >= min_confidence`.
3. For each surviving tag, increments `self._tag_stats[tag.name]` by 1.
4. Returns `TagResult(content=content, tags=tags)`.

**Side effects:** mutates `self._tag_stats` (one increment per surviving tag).
Note the statistics count only tags that pass the `min_confidence` filter,
not every tag the detector emitted.

#### `batch_tag(self, contents: list[str]) -> list[TagResult]`
Returns `[self.tag(c) for c in contents]` — calls `tag` with the default
`min_confidence=0.0` for each item. **Guard path:** empty list → `[]`.

#### `get_tag_statistics(self) -> dict[str, int]`
Returns a copy (`dict(self._tag_stats)`) of the accumulated per-tag counts.

#### `add_topic(self, name: str, keywords: list[str])`
Delegates to `self._detector.add_topic(name, keywords)` (no `weight`
parameter exposed here).

#### `clear_statistics(self)`
`self._tag_stats.clear()`.

## Contract holes

1. **Substring (non-word-boundary) keyword matching:** `detect()` counts
   occurrences with `re.findall(re.escape(kw_lower), text_lower)`, which
   matches keywords as substrings, not whole words. Short keywords therefore
   match inside longer words: `"ai"` matches inside "said"/"maintain",
   `"sql"` inside "nosql", `"index"` inside "indexes", `"model"` inside
   "modeling", `"training"` inside "retraining". The docstring says "keyword
   occurrences" without stating the substring semantics, so a reader who
   expects word-boundary matching will be surprised by false-positive topic
   matches. → **ARCH-19** (ticketed).

2. **Dead `weight` field:** `_TopicDefinition.weight` is stored (default
   `1.0`) and `TopicDetector.add_topic(..., weight=...)` accepts it, but
   `detect()`'s confidence formula (`0.5 + match_count * 0.1`) never reads
   `weight`. The parameter is silently ignored, so callers who pass a weight
   to bias a topic get no effect. → **ARCH-19** (ticketed, same contract).

3. **Statistics count only surviving tags:** `tag()` increments
   `self._tag_stats` only for tags that pass the `min_confidence` filter, so
   `get_tag_statistics()` under-reports total detections when a caller uses
   a non-zero `min_confidence`. This is defensible (statistics = "tags
   actually returned") but is not stated in the docstring.
