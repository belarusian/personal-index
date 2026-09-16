# interests — `personal_index.interests`

Spec page (matches CURRENT code as of cycle 253).

`interests.py` is the CLI-facing persistent store for user interests. It
exposes one public type, the `InterestStore` dataclass, which owns a
`dict[str, Interest]` keyed by interest name and persists it to a JSON file.
It does **not** own the `Interest` value type — that lives in
`personal_index.models` (see `docs/content-model.md`). This page documents
`personal_index.interests` (`InterestStore` — user interest
scoring/keywords/persistence + pipeline scoring/filtering influence), which is
**DIFFERENT** from the other scoring/filter/tagging modules:

- `personal_index.content_scoring` (`docs/scoring.md`) — `ContentScorer`
  scores *crawled pages*, not user interests.
- `personal_index.content_filter` (`docs/content-filter.md`) — `ContentFilter`
  decides page inclusion; it *consumes* an `InterestStore` but is a separate
  module.
- `personal_index.content_tagger` (`docs/content-tagger.md`) — `TopicDetector`
  / `ContentTagger` tag pages with topics; unrelated to user interests.
- `personal_index.content_priority` (`docs/content-priority.md`) —
  `PriorityCalculator` ranks items; it *reads* interest scores but is a
  separate module.

`InterestStore` is the single source of the keyword / url-pattern / topic
sets that `ContentFilter`, `ContentScorer`, and `PriorityCalculator` draw on,
so a load failure here silently degrades every downstream scoring/filtering
decision.

## `InterestStore` (dataclass, line 15)

Fields (in declaration order): `store_path: str | None = None` (line 18),
`_interests: dict[str, Interest]` (line 19, `repr=False`, `default_factory=dict`).

- `__post_init__(self)` (line 23): if `store_path` is truthy **and** the file
  exists, calls `_load()`. A `None` path or a missing file leaves the store
  empty (in-memory mode).
- `_load(self) -> None` (line 27): returns immediately when `store_path` is
  falsy. Otherwise reads the file and `json.load`s it. If the parsed value is
  **not a dict**, `_interests` is set to `{}` and it returns. Otherwise it
  rebuilds `_interests` as `{name: Interest.from_dict(d) for name, d in
  data.items()}`. The whole read/rebuild is wrapped in
  `except (json.JSONDecodeError, KeyError, TypeError, AttributeError,
  ValueError)`, which sets `_interests = {}`. **Confirmed contract (ARCH-85,
  Option A):** the except tuple includes `ValueError`, so a record whose
  `interest_type` or `match_mode` is an out-of-enum string (which
  `Interest.from_dict` coerces via `InterestType(...)` / `MatchMode(...)` at
  models.py lines 79-84, raising `ValueError`) degrades to the same empty
  store as every other bad input — the constructor never raises on file
  contents. See ARCH-85.
- `_save(self) -> None` (line 44): returns immediately when `store_path` is
  falsy. Otherwise `os.makedirs(os.path.dirname(store_path) or ".",
  exist_ok=True)`, then writes `{name: interest.to_dict() for ...}` as
  indented JSON. The write is a **direct** `open(..., "w")` + `json.dump` —
  non-atomic (no temp-file-and-rename), so an interrupted write truncates the
  file; the next `_load` then degrades to `{}` (see the ARCH-85 note: the
  truncation itself is caught, the enum `ValueError` is not).
- `add(self, interest: Interest) -> None` (line 58): stores
  `self._interests[interest.name] = interest` (replaces an existing interest
  with the same name) and calls `_save()`.
- `remove(self, name: str) -> bool` (line 63): deletes `name` and calls
  `_save()`, returning `True`; returns `False` (no save) when `name` is
  absent.
- `get(self, name: str) -> Interest | None` (line 71): returns the stored
  `Interest` or `None`.
- `list_all(self) -> list[Interest]` (line 75): returns a **new list** of all
  values (insertion order).
- `get_enabled(self) -> list[Interest]` (line 79): returns a new list of the
  interests with `enabled` truthy.
- `toggle(self, name: str) -> Interest | None` (line 83): returns `None` when
  `name` is absent; otherwise flips `interest.enabled`, calls `_save()`, and
  returns the interest.
- `get_all_keywords(self) -> set[str]` (line 92): the union of every
  **string** element of every interest's `keywords`, lowercased; non-string
  elements are skipped.
- `get_all_url_patterns(self) -> list[re.Pattern]` (line 102): compiles every
  **string** element of every interest's `url_patterns`; non-string elements
  are skipped and a pattern raising `re.error` is skipped (via
  `suppress(re.error)`), so it never raises.
- `get_all_topics(self) -> set[str]` (line 113): the union of every **string**
  element of every interest's `topics`, lowercased; non-string elements are
  skipped.
- `update_priority(self, name: str, priority: int) -> Interest | None`
  (line 123): returns `None` when `name` is absent; otherwise sets
  `interest.priority = max(1, min(10, priority))` (clamped 1-10), calls
  `_save()`, and returns the interest.
- `matches_any(self, text: str, url: str = "") -> list[Interest]` (line 132):
  returns every interest for which `interest.matches(text, url)` is truthy
  (delegates to `Interest.matches`, models.py — disabled interests never
  match).
- `clear(self) -> None` (line 141): empties `_interests` and calls `_save()`.
- `total_score(self, text: str) -> float` (line 146): `sum(interest.score(text)
  for ...)` across all interests (delegates to `Interest.score`, models.py —
  disabled interests contribute `0.0`).

## Invariants
- The store is keyed by `interest.name`; `add` is a replace-on-collision
  (last write wins), not an append.
- Every mutating method (`add`, `remove`, `toggle`, `update_priority`,
  `clear`) calls `_save()`; every read method is side-effect-free.
- `get_all_keywords` / `get_all_topics` are case-folded (lowercased) sets;
  `get_all_url_patterns` is an ordered list of compiled patterns.
- `update_priority` clamps to `[1, 10]`; `Interest.__post_init__` (models.py)
  also clamps on construction, so a priority outside the range never persists
  unclamped.
- In-memory mode (`store_path=None`) is fully functional; `_load`/`_save` are
  no-ops.

## Persistence
- File format: a JSON object mapping `name -> Interest.to_dict()` (the
  `Interest` fields, with `interest_type` / `match_mode` serialized to their
  string values).
- `_load` degrades to an empty store for: missing file, invalid JSON
  (`json.JSONDecodeError`), a parsed value that is not a dict, a record value
  that is not a dict (`from_dict` → `.get` raises `AttributeError`, caught),
  a record missing `name` (dataclass constructor raises `TypeError`, caught),
  and a record whose `interest_type` or `match_mode` is an out-of-enum string
  (`InterestType(...)` / `MatchMode(...)` raises `ValueError`, caught —
  ARCH-85 Option A). The except tuple is
  `(json.JSONDecodeError, KeyError, TypeError, AttributeError, ValueError)`.
- `_save` is non-atomic (direct write); an interrupted write truncates the
  file, and the next `_load` degrades to `{}` (the truncation is caught, but
  the data is lost with no signal).

## `_load` graceful degradation — CONFIRMED contract (ARCH-85, Option A)
`_load` promises graceful degradation for bad file contents, and its except
tuple `(json.JSONDecodeError, KeyError, TypeError, AttributeError, ValueError)`
covers every malformed-record shape **including** an out-of-enum
`interest_type` or `match_mode`. `Interest.from_dict` (models.py lines 79-84)
does `InterestType(interest_type)` / `MatchMode(match_mode)` on the raw
string, which raises `ValueError` for any value not in the enum — and
`ValueError` is now caught. So a valid-JSON-dict file with a corrupted enum
value (e.g. `{"foo": {"name": "foo", "interest_type": "bogus"}}`) degrades to
an empty store (`list_all() == []`) instead of crashing the `InterestStore`
constructor. The architect resolved the open choice in cycle 289 by
confirming **Option A (add `ValueError` to the except tuple — lossless,
minimal, symmetric with the existing structural-error tuple)** as the
contract. The existing tests pin the corrupt-JSON / non-dict / null /
non-dict-value / missing-`name` guards; the corrected contract is pinned by
the new out-of-enum pins named in ARCH-85 (a valid-dict record with an
out-of-enum `interest_type` and one with an out-of-enum `match_mode`, each
asserting no raise and `list_all() == []`), which are the witness that this
corrected contract matches the implemented behavior. See
`tickets/ARCH-85.md`.
