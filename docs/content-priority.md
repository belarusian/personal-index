# content-priority — Exact Contract

Module: `personal_index/content_priority.py` (239 lines)

Content priority scoring for assigning a priority level to content items from
multiple factors (recency, content score, interest match, user engagement).
Four public types: `PriorityLevel` (a 5-member `Enum` with a `from_score`
classmethod), `PriorityConfig` (an 8-field `@dataclass` of weights +
thresholds), `PriorityResult` (a 6-field `@dataclass` with `to_dict`), and
`PriorityCalculator` (the scoring engine: `calculate`, `batch_calculate`,
`get_summary` plus private factor helpers). There is no I/O and no state
beyond the injected `PriorityConfig`; the calculator is pure and
single-threaded by contract.

## Public API

### PriorityLevel

`Enum` with 5 members (value = lowercase string):

- `CRITICAL = "critical"`
- `HIGH = "high"`
- `MEDIUM = "medium"`
- `LOW = "low"`
- `ARCHIVE = "archive"`

`from_score(cls, score: float) -> PriorityLevel` (classmethod): maps a
normalized score to a level using **hardcoded** bands (it does NOT read
`PriorityConfig`):

- `score >= 0.8` → `CRITICAL`
- `score >= 0.6` → `HIGH`
- `score >= 0.4` → `MEDIUM`
- `score > 0` (strictly greater than zero) → `LOW`
- otherwise (`score <= 0`) → `ARCHIVE`

Note the asymmetric boundary: the top three bands are inclusive (`>=`) but the
LOW band is `score > 0`, so `score == 0` is `ARCHIVE`, not `LOW`, and any
score in `(0, 0.4)` is `LOW`.

### PriorityConfig

`@dataclass` with 8 fields (all `float`):

- `recency_weight: float = 0.2`
- `score_weight: float = 0.3`
- `interest_weight: float = 0.3`
- `engagement_weight: float = 0.2`
- `critical_threshold: float = 0.8`
- `high_threshold: float = 0.6`
- `medium_threshold: float = 0.4`
- `low_threshold: float = 0.2`

The default weights sum to exactly `1.0`; the default thresholds are the same
numeric bands as `PriorityLevel.from_score`'s hardcoded bands (0.8 / 0.6 /
0.4) plus a `low_threshold` of 0.2 that `from_score` does not have.

### PriorityResult

`@dataclass` with 6 fields:

- `url: str`
- `title: str`
- `priority: PriorityLevel`
- `score: float`
- `breakdown: dict[str, float] = field(default_factory=dict)`
- `factors: list[str] = field(default_factory=list)`

`to_dict(self) -> dict[str, Any]` returns:

- `"url"`: `self.url`
- `"title"`: `self.title`
- `"priority"`: `self.priority.value` (the lowercase string, not the enum)
- `"score"`: `round(self.score, 4)`
- `"breakdown"`: `{k: round(v, 4) for k, v in self.breakdown.items()}`
- `"factors"`: `self.factors` (copied by reference, not rounded)

### PriorityCalculator

Plain class (not a dataclass). `__init__(self, config: PriorityConfig | None =
None)`: `self.config = config or PriorityConfig()` (a fresh default config is
used when `config` is `None`).

Public methods:

- `calculate(self, url: str, title: str, content_score: float = 0.0,
  interest_matches: list[str] | None = None, view_count: int = 0,
  days_since_indexed: float = 0.0) -> PriorityResult` — computes four
  sub-factors, each recorded in `breakdown`, then a weighted total:
  - `recency` = `_recency_score(days_since_indexed)`; added via `_add_factor`
    as label `"recently indexed"` when `> 0.7`.
  - `content_score` = `min(max(content_score / 10.0, 0.0), 1.0)` (the input
    is on a 0-10 scale, normalized to 0-1 and clamped); added via `_add_factor`
    as label `"high content score"` when `> 0.7`.
  - `interest_match` = `_interest_score(interest_matches or [])`; the
    `breakdown["interest_match"]` key is always set, and a
    `"matches interests: <first 3>"` factor is appended when
    `interest_matches` is non-empty (this path does NOT use `_add_factor`).
  - `engagement` = `_engagement_score(view_count)`; the
    `breakdown["engagement"]` key is always set, and a
    `"high engagement (<view_count> views)"` factor is appended when
    `view_count > 10` (this path does NOT use `_add_factor`).
  - `total` = `_weighted_total(recency, content_score, interest_match,
    engagement)`; the returned `PriorityResult` has `priority =
    _level_for_score(total)`, `score = total`, plus `breakdown` and `factors`.

- `batch_calculate(self, items: list[dict[str, Any]]) -> list[PriorityResult]`
  — for each item dict, calls `calculate` with `item.get("url", "")`,
  `item.get("title", "")`, `item.get("content_score", 0.0)`,
  `item.get("interest_matches", [])`, `item.get("view_count", 0)`,
  `item.get("days_since_indexed", 0.0)`; then sorts the results by `score`
  **descending** (Python's stable sort, so equal scores keep input order) and
  returns them. It does NOT deduplicate: two items with the same `url`
  produce two results.

- `get_summary(self, results: list[PriorityResult]) -> dict[str, int]` —
  counts results per `PriorityLevel.value`; only levels that are PRESENT in
  `results` appear as keys (absent levels are omitted, not zero-valued), and
  an empty `results` list returns `{}`.

Private factor helpers (documented here because `calculate`'s contract
depends on their exact math):

- `_add_factor(self, factors, breakdown, name, value, label, threshold=0.7)
  -> None` — sets `breakdown[name] = value`; appends `label` to `factors`
  only when `value > threshold` (strict).
- `_weighted_total(self, r, s, i, e) -> float` —
  `r*recency_weight + s*score_weight + i*interest_weight +
  e*engagement_weight`. It does NOT normalize by the weight sum, so the
  result is only guaranteed to be in `[0, 1]` when the config weights sum to
  `1.0`.
- `_recency_score(self, days_since_indexed: float) -> float` —
  `math.exp(-days_since_indexed / 30.0)` (1.0 at day 0, decaying toward 0).
- `_interest_score(self, matches: list[str]) -> float` — `0.0` when empty,
  else `min(len(matches) * 0.25, 1.0)` (saturates at 4 matches).
- `_engagement_score(self, view_count: int) -> float` — `0.0` when
  `view_count <= 0`, else `min(1.0, math.log(1 + view_count) /
  math.log(101))` (saturates at 100 views).
- `_level_for_score(self, score: float) -> PriorityLevel` — maps a weighted
  total to a level using the **config** thresholds: `score >=
  critical_threshold` → `CRITICAL`, `>= high_threshold` → `HIGH`, `>=
  medium_threshold` → `MEDIUM`, `>= low_threshold` → `LOW`, else `ARCHIVE`.
  All four boundaries are inclusive (`>=`), so `score == 0.2` is `LOW` and
  `score < 0.2` is `ARCHIVE`.

## Contract Holes

**Primary hole — two divergent public score→level paths (ARCH-45).** The
module exposes TWO independent ways to convert a score to a `PriorityLevel`,
and they are not equivalent:

- `PriorityLevel.from_score(score)` uses **hardcoded** bands and returns
  `LOW` for any `score > 0` (i.e. `(0, 0.4)` → `LOW`, `score <= 0` →
  `ARCHIVE`).
- `PriorityCalculator._level_for_score(score)` uses the **config** thresholds
  and returns `LOW` only for `score >= low_threshold` (default `0.2`), so
  `score < 0.2` → `ARCHIVE`.

For any score in `(0, 0.2)` the two paths DISAGREE: `from_score` → `LOW`,
`_level_for_score` → `ARCHIVE`. Worse, `from_score` ignores `PriorityConfig`
entirely, so a caller who tunes `low_threshold` (or any threshold) in the
config has NO effect on `from_score` — the two public entry points to
"score → level" can return different levels for the same score, and the
contract never states which is authoritative or that they are meant to
differ. This is an underspecified semantic, not a boundary nit: an implementer
or caller cannot tell whether `from_score` is a standalone convenience or a
second (drifted) implementation of the same mapping.

The fix must make the relationship explicit (pick one and document it in the
`from_score` docstring + this page):

- **Option A (single source of truth):** route `from_score` through the same
  band logic driven by the default `PriorityConfig` thresholds, so both paths
  agree for the default config and the `> 0` / `>= 0.2` LOW boundary is
  reconciled to one rule.
- **Option B (documented divergence):** state that `from_score` is a
  standalone convenience with its own fixed bands (independent of
  `PriorityConfig`) and that `_level_for_score` is the config-driven path
  used by `calculate`/`batch_calculate`, and pin the exact boundary values of
  each so the disagreement is intentional and witnessed.

## Secondary notes (not ticketed)

- `_weighted_total` does NOT normalize by the weight sum: if a custom
  `PriorityConfig` has weights that do not sum to `1.0`, the weighted total
  (and thus `PriorityResult.score`) can exceed `1.0` or stay below it, even
  though every sub-factor is in `[0, 1]`. The contract never states that the
  weights are assumed to sum to `1.0`.
- `batch_calculate` sorts by `score` descending but does NOT deduplicate:
  duplicate `url`s yield duplicate results, and equal scores keep input order
  (stable sort). Neither behavior is stated in the contract.
- `calculate` records `interest_match` and `engagement` in `breakdown`
  unconditionally, but appends their `factors` labels by rules different from
  `recency`/`content_score` (which use `_add_factor`'s `> 0.7` threshold):
  the interest label fires on non-empty `interest_matches`, the engagement
  label on `view_count > 10`. So `breakdown` keys and `factors` entries are
  not in lockstep.
- `_engagement_score` saturates at exactly 100 views
  (`log(101)/log(101) == 1.0`); `_interest_score` saturates at 4 matches.
- `to_dict` rounds `score` and each `breakdown` value to 4 places but returns
  `priority` as its `.value` string and `factors` unmodified.
