# Content Recommender (spec)

`personal_index.content_recommender` — content recommendation engine.
Recommends related content based on keyword overlap, tag similarity, and
existing scores. No external dependencies; pure `re` + `dataclasses`.

## Public API

### `Recommendation` (dataclass)
The return object of every public method. Fields, in order:
- `url: str` — the recommended item's URL.
- `title: str` — the recommended item's title.
- `score: float` — the combined / matched score (see each method).
- `reason: str` — a human-readable reason string (see each method).
- `matching_keywords: list[str]` — the common keywords (default `[]`).
- `matching_tags: list[str]` — the common tags (default `[]`).
- `to_dict() -> dict[str, Any]` — returns a dict with keys `url`, `title`,
  `score` (rounded to 4 decimals), `reason`, `matching_keywords`,
  `matching_tags`.

### `ContentItem` (dataclass)
The input item type. Fields, in order:
- `url: str` — the item's URL (used to exclude the seed in `recommend`).
- `title: str` — the item's title.
- `content: str` — the item's body text (default `""`).
- `keywords: list[str]` — explicit keywords (default `[]`).
- `tags: list[str]` — explicit tags (default `[]`).
- `score: float` — an existing score in `[0, 10]` (default `0.0`).
- `all_keywords` (property) -> `set[str]` — the union of `set(self.keywords)`
  plus `_extract_keywords(self.content)` plus `_extract_keywords(self.title)`.
  Note: the explicit `self.keywords` are added **as-is** (case-sensitive); only
  the content/title-derived keywords are lowercased by `_extract_keywords`.

### `Recommender`
The recommendation engine.

#### `__init__(self, min_score: float = 0.1)`
Stores `min_score` and initializes an empty `_items` list.

#### `add_item(self, item: ContentItem) -> None`
Appends `item` to the pool.

#### `add_items(self, items: list[ContentItem]) -> None`
Extends the pool with `items`.

#### `recommend(self, seed: ContentItem, top_n: int = 5, keyword_weight: float = 0.6, tag_weight: float = 0.3, score_weight: float = 0.1) -> list[Recommendation]`
Behavior, in order:
1. **Guard path:** if the pool is empty (`not self._items`), return `[]`.
2. For each item in the pool, **skip** the seed itself (matched by
   `item.url == seed.url`).
3. For each remaining item compute two Jaccard sub-scores:
   - `_keyword_overlap_score(seed, item)` -> `(kw_score, kw_common)` where
     `kw_score = len(common) / len(union)` over `all_keywords` (0.0 when either
     side has no keywords), `kw_common = sorted(common)`.
   - `_tag_similarity_score(seed, item)` -> `(tag_score, tag_common)` where
     `tag_score = len(common) / len(union)` over `set(tags)` (0.0 when either
     side has no tags), `tag_common = sorted(common)`.
4. `_build_recommendation(item, kw_score, kw_common, tag_score, tag_common,
   keyword_weight, tag_weight, score_weight)` -> `Recommendation | None`:
   - `norm = min(item.score / 10.0, 1.0)` when `item.score > 0` else `0.0`.
   - `combined = kw_score * keyword_weight + tag_score * tag_weight +
     norm * score_weight`.
   - **Guard path:** if `combined < self.min_score`, return `None` (item
     dropped).
   - `reason` is `"; ".join` of `"keywords: <top-5 common>"` (when
     `kw_common`) and/or `"tags: <all common>"` (when `tag_common`), or
     `"score-based"` when neither matched.
   - Returns `Recommendation(url, title, score=combined, reason,
     matching_keywords=kw_common, matching_tags=tag_common)`.
5. Survivors are sorted by `score` (descending) and truncated to `top_n`.
   **Contract hole:** the truncation is `candidates[:top_n]` with no guard for
   `top_n < 0` — a negative `top_n` leaks Python negative-slice semantics
   (returns all-but-last instead of `[]`). See ARCH-15.

#### `recommend_for_keywords(self, keywords: list[str], top_n: int = 5) -> list[Recommendation]`
Behavior, in order:
1. `keyword_set = {kw.lower() for kw in keywords if kw}` — query keywords are
   lowercased and empty strings dropped.
2. **Guard path:** if `keyword_set` is empty, return `[]`.
3. For each item in the pool, `common = keyword_set & item.all_keywords`; if
   `common` is non-empty, `score = len(common) / len(keyword_set)` (the matched
   fraction). **Guard path:** if `score < self.min_score`, the item is dropped.
   Otherwise append `Recommendation(url, title, score, reason=f"matched
   keywords: <sorted common>", matching_keywords=sorted(common))`.
4. Survivors are sorted by `score` (descending) and truncated to `top_n`.
   **Contract hole:** the truncation is `candidates[:top_n]` with no guard for
   `top_n < 0` — a negative `top_n` leaks Python negative-slice semantics
   (returns all-but-last instead of `[]`). See ARCH-15.
   **Contract hole:** the docstring claims "matching is case-insensitive", but
   only the *query* keywords are lowercased; an item's explicit `keywords` are
   matched case-sensitively (only content/title-derived keywords are
   lowercased). See ARCH-16.

#### `clear(self) -> None`
Clears the pool.

#### `item_count` (property) -> `int`
Returns `len(self._items)`.

## Private helpers (the code is the truth)
- `_extract_keywords(text: str) -> set[str]` — **Guard path:** returns `set()`
  when `text` is falsy. Otherwise `re.findall(r'[a-z0-9]+', text.lower())`,
  drops stopwords (a fixed frozenset of ~70 English function words) and words
  of length `<= 2`. Returns the surviving lowercase tokens as a set.
- `_keyword_overlap_score(a, b) -> tuple[float, list[str]]` — Jaccard over
  `all_keywords`; returns `(0.0, [])` when either side has no keywords.
- `_tag_similarity_score(a, b) -> tuple[float, list[str]]` — Jaccard over
  `set(tags)`; returns `(0.0, [])` when either side has no tags.
- `_build_recommendation(item, kw_score, kw_common, tag_score, tag_common,
  kw_w, tag_w, sc_w) -> Recommendation | None` — see `recommend` step 4.

## Contract holes
- **ARCH-15** — `recommend` and `recommend_for_keywords` both truncate with
  `candidates[:top_n]` and have no guard for `top_n < 0`; a negative `top_n`
  leaks Python negative-slice semantics (returns all-but-last instead of `[]`).
  This is the same class as QA-1 (`KeywordExtractor.extract_top_n` negative
  `n`) — the negative-slice-truncation class recurs across modules.
- **ARCH-16** — `recommend_for_keywords` docstring over-promises "matching is
  case-insensitive"; only the query keywords are lowercased, so an item's
  explicit `keywords` are matched case-sensitively.
