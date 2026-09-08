# search_suggestions — spec

`personal_index.search_suggestions`: autocomplete + related-query generation
from in-memory search history, tags, keywords, and time-decayed trending
queries. **Passive generator** — it holds suggestion state in memory and
produces `Suggestion` objects; it performs no I/O and no persistence itself
(the caller serializes via `to_dict` / `from_dict`).

## Public API

### `Suggestion` (dataclass)
Fields: `text: str`, `score: float = 0.0`, `source: str = "unknown"`
(one of `"history"`, `"tags"`, `"keywords"`, `"trending"`, `"related"`),
`category: str = ""`.
- `to_dict() -> dict[str, Any]`: returns a **new** dict with exactly the keys
  `text`, `score`, `source`, `category`. `score` is rounded to 4 decimal
  places (`round(self.score, 4)`); `text`, `source`, and `category` are copied
  by reference. The `Suggestion` object is **not** mutated.

### `TrendingEntry` (dataclass)
Fields: `query: str`, `count: int = 1`, `first_seen: float` (auto-set to
`time.time()`), `last_seen: float` (auto-set to `time.time()`).
- `age_seconds -> float` (property): `time.time() - self.last_seen`.
- `record() -> None`: increments `count` and refreshes `last_seen` to now.

### `SearchSuggestions`
Constructor: `SearchSuggestions(max_suggestions: int = 10,
min_prefix_length: int = 2, fuzzy_threshold: float = 0.3,
decay_half_life: float = 3600.0)`.
State: `_search_history: list[str]`, `_tags: list[str]`,
`_keywords: list[str]`, `_trending: dict[str, TrendingEntry]` (keyed by
lower-cased query).

- `add_search_history(queries: list[str]) -> None`: extends history.
- `add_tags(tags: list[str]) -> None`: extends tags.
- `add_keywords(keywords: list[str]) -> None`: extends keywords.
- `record_search(query: str) -> None`: appends `query` to history **and**
  records it in `_trending` (keyed by `query.lower()`); an existing key
  calls `TrendingEntry.record()`, a new key creates a `TrendingEntry`.
- `get_trending(n: int = 10) -> list[str]`: returns the top-`n` trending
  queries (original case) sorted by **decayed** score descending
  (`count * 0.5 ** (age / decay_half_life)`; raw `count` when
  `decay_half_life <= 0`).
- `suggest(prefix: str, sources: list[str] | None = None,
  fuzzy: bool = False) -> list[Suggestion]`:
  - **Guard:** if `len(prefix) < min_prefix_length`, returns `[]` (no
    candidates are gathered).
  - `sources=None` searches all four sources; otherwise only the named ones
    (`"history"`, `"tags"`, `"keywords"`, `"trending"`).
  - Exact matches are `query.lower().startswith(prefix.lower())`.
  - Per-source score weights: history `min(count/len(history)*10, 1.0)`,
    tags `* 0.9`, keywords `* 0.8`, trending `* 1.1` (see contract holes).
  - `fuzzy=True` additionally admits non-prefix candidates whose
    `_fuzzy_match_score(prefix, candidate) >= fuzzy_threshold`, with
    per-source fuzzy multipliers (history `*0.7`, tags `*0.6`, keywords
    `*0.5`, trending `*0.9`).
  - Returns the top `max_suggestions` by score descending.
- `get_related_queries(query: str, n: int = 5) -> list[Suggestion]`:
  word-overlap related queries from history. Splits `query` and each history
  entry on whitespace; a history entry qualifies when it is not equal to
  `query` (case-insensitive) and shares at least one word. Score is the
  overlap ratio `len(shared)/len(query_words)`, accumulated per history
  entry. Returns the top `n` as `Suggestion(source="related",
  category="related_query")`.
- `clear() -> None`: empties history, tags, keywords, and trending.
- `to_dict() -> dict[str, Any]`: serializes `search_history`, `tags`,
  `keywords`, and `trending` (each trending entry as a dict with `query`,
  `count`, `first_seen`, `last_seen`).
- `from_dict(data: dict[str, Any]) -> SearchSuggestions` (classmethod):
  deserializes; tolerates the legacy trending shape where a value is a bare
  `int`/`float` count (`{query: count}`) as well as the current dict shape.

### Module-level scoring helpers (private)
- `_exact_or_prefix_match(q_lower, c_lower) -> float | None`: `1.0` on exact
  match; on prefix, `max(0.9, 0.7 + (len(q)/max(len(c),1)) * 0.3)`; `None`
  otherwise.
- `_sequence_with_containment(q_lower, c_lower) -> float`: `max` of the
  `SequenceMatcher` ratio and a character-containment bonus
  (`len(q_chars & c_chars)/len(q_chars) * 0.8`).
- `_fuzzy_match_score(query, candidate) -> float`: **guard** — returns `0.0`
  when either argument is empty. Otherwise exact/prefix (above), `0.8` when
  `q_lower in c_lower`, else `_sequence_with_containment`. Documented to
  return a score in `[0.0, 1.0]`.

## Contract holes
- **Trending exact-match score can exceed 1.0.** In `_suggest_from_trending`,
  the exact-match branch computes
  `score = min(decayed / max(total_decayed, 1) * 10, 1.0)` and then stores
  `Suggestion(score=score * 1.1)`. Because the multiplier is applied **after**
  the `min(..., 1.0)` clamp, a single dominant trending entry (its own
  decayed score == the total, so the base clamps to `1.0`) yields a final
  `Suggestion.score` of **`1.1`** — outside the `[0.0, 1.0]` range that
  `_fuzzy_match_score`'s docstring and every other source's weight imply.
  Guard path that exposes it: `record_search("python")` once, then
  `suggest("py")` → the trending suggestion's `score` is `1.1`.
  See `tickets/ARCH-30.md`.
