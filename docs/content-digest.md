# content-digest — Exact Contract

Module: `personal_index/content_digest.py` (273 lines, stdlib-only imports:
`dataclasses`, `datetime`, `typing`).

Generates daily/weekly digests of new and updated content, grouped by
topic/tag or source. Four public types: `DigestEntry` (one item),
`DigestSection` (a grouped bucket), `ContentDigest` (the assembled report,
with `to_dict` / `format_markdown` / `format_text`), and `DigestGenerator`
(the engine: `add_entry` / `add_entries` / `generate` / `clear` plus the
private grouping/summary helpers). There is **no** persistence layer of its
own: `DigestGenerator` holds entries in an in-memory list and `generate`
returns a `ContentDigest` value; the caller owns any serialization
(`to_dict`) or rendering (`format_markdown` / `format_text`). All timestamps
are ISO-8601 UTC strings; the module never parses a caller-supplied
`period_start`/`period_end` — it only substitutes a default when one is
falsy.

## Public API

### DigestEntry

`@dataclass`. Fields (in order):

- `url: str`
- `title: str`
- `summary: str`
- `tags: list[str] = field(default_factory=list)`
- `score: float = 0.0`
- `timestamp: str = ""`
- `source: str = ""`

`to_dict(self) -> dict[str, Any]`: returns a fresh dict with exactly the keys
`url`, `title`, `summary`, `tags`, `score`, `timestamp`, `source`, in that
order. `tags` is the **same list object** (not a copy), so mutating the
returned dict's `tags` mutates the entry.

### DigestSection

`@dataclass`. Fields:

- `topic: str`
- `entries: list[DigestEntry] = field(default_factory=list)`

`count` is a **`@property`** (not a method): `count(self) -> int` returns
`len(self.entries)`. Callers read `section.count`, never `section.count()`.

### ContentDigest

`@dataclass`. Fields (in order):

- `title: str`
- `generated_at: str`
- `period_start: str`
- `period_end: str`
- `sections: list[DigestSection] = field(default_factory=list)`
- `total_entries: int = 0`
- `summary: str = ""`

`to_dict(self) -> dict[str, Any]`: returns a fresh dict with keys `title`,
`generated_at`, `period_start`, `period_end`, `sections`, `total_entries`,
`summary`. Each section is rendered as `{"topic": s.topic, "entries":
[e.to_dict() for e in s.entries]}` — i.e. the nested entries are deep-copied
via their own `to_dict` (so the returned dict does not alias the live
`DigestEntry` objects, though each entry's `tags` list is still aliased per
`DigestEntry.to_dict`).

`format_markdown(self) -> str`: renders the digest as Markdown.

- Header block: `# {title}`, blank line, `**Generated:** {generated_at}`,
  `**Period:** {period_start} to {period_end}`, `**Total entries:**
  {total_entries}`, blank line.
- If `summary` is truthy: a blockquote line `> {summary}` + blank line.
- For each section: `## {topic}`, blank line, then for each entry a heading
  `### [{entry.title}]({entry.url})`; if `entry.summary` is truthy a line with
  the summary; if `entry.tags` is truthy a line `Tags: {', '.join(tags)}`;
  then a blank line.
- Returns `"\n".join(lines)`. **No escaping is applied** to any field
  (title, url, summary, tags, or the H1 title) — see Contract Holes.

`format_text(self) -> str`: renders the digest as plain text.

- Header block: `{title}`, a line of `=` repeated `len(title)` times,
  `Generated: {generated_at}`, `Period: {period_start} to {period_end}`,
  `Total entries: {total_entries}`, blank line.
- If `summary` is truthy: the summary line + blank line.
- For each section: `[{topic}]`, a line of `-` repeated `len(topic)` times,
  then for each entry `  • {entry.title}`, `    {entry.url}`, and — **only if
  `entry.summary` is truthy** — `    {entry.summary[:100]}` (the summary is
  truncated to 100 characters); then a blank line.
- Returns `"\n".join(lines)`.

Note the **format divergence**: `format_markdown` emits the full `entry.summary`
verbatim and a `Tags:` line; `format_text` truncates the summary to 100 chars
and emits **no tags line at all**. The two renderers are not interchangeable
views of the same content.

### DigestGenerator

Plain class (not a dataclass).

`__init__(self) -> None`: sets `self._entries: list[DigestEntry] = []`.

`add_entry(self, entry: DigestEntry) -> None`: appends one entry to the
accumulated list.

`add_entries(self, entries: list[DigestEntry]) -> None`: extends the
accumulated list with `entries`.

`generate(self, title: str = "Content Digest", period_start: str | None = None,
period_end: str | None = None, group_by: str = "tags",
max_entries_per_section: int = 10) -> ContentDigest`:

- `now = datetime.now(timezone.utc).isoformat()` is computed once and used as
  both `generated_at` and the default `period_end`.
- Entries are **sorted by `score` descending** (`sorted(self._entries,
  key=lambda e: e.score, reverse=True)`) before grouping. The sort is stable,
  so equal-score entries keep their insertion order.
- `sections = self._resolve_sections(entries, group_by,
  max_entries_per_section)` (see below).
- `summary = self._generate_summary(sections, total_entries=len(entries))`
  (see below). Under the ARCH-49 Option A contract the summary's
  "N new items" figure **always equals `total_entries`** (the
  distinct-entry count); it is NOT the sum of the per-section (capped)
  counts, so multi-tag entries are not double-counted and the per-section
  cap does not deflate the headline number.
- Returns `ContentDigest(title=title, generated_at=now,
  period_start=period_start or (now - 7 days).isoformat(),
  period_end=period_end or now, sections=sections,
  total_entries=len(entries), summary=summary)`.
  - `period_start`/`period_end` are used verbatim when truthy; when falsy
    they default to `now - 7 days` and `now` respectively. They are **never
    parsed or validated** — a malformed string is passed through unchanged.
  - `total_entries` is `len(entries)` — the count of **distinct** accumulated
    entries (after sorting, before per-section capping). This is NOT the sum
    of the section counts — see Contract Holes.

`clear(self) -> None`: clears the accumulated entry list.

### Private helpers (referenced for exact semantics)

- `_resolve_sections(self, entries, group_by, max_per_section) ->
  list[DigestSection]`: dispatches on `group_by`. `"none"` → a single section
  `topic="All Content"` holding `entries[:max_per_section]`. `"source"` →
  `_group_by_source`. **Anything else** (including `"tags"` and any
  unrecognized string) → `_group_by_tags`. There is no validation of
  `group_by`; an unrecognized value silently falls through to tag grouping.
- `_group_by_tags(self, entries, max_per_section) -> list[DigestSection]`:
  for each entry, if `entry.tags` is truthy the entry is appended to **every**
  tag's bucket (`tag_entries.setdefault(tag, []).append(entry)` for each tag);
  otherwise it is appended to an `untagged` list. Sections are built for each
  tag in `sorted(tag_entries.keys())` order, each capped at
  `max_per_section` entries; a non-empty `untagged` list becomes a final
  `topic="Uncategorized"` section, also capped. **Because a multi-tag entry is
  placed in every tag's bucket, the sum of the section counts can exceed the
  number of distinct entries** — see Contract Holes.
- `_group_by_source(self, entries, max_per_section) -> list[DigestSection]`:
  buckets entries by `entry.source or "Unknown"` (a falsy `source` maps to the
  literal topic `"Unknown"`). Sections are built in `sorted(source_entries.
  keys())` order, each capped at `max_per_section`. Each entry lands in
  exactly one bucket, so the section-count sum equals the distinct-entry count
  here (before capping).
- `_generate_summary(self, sections, total_entries) -> str`: `total =
  total_entries` (the distinct-entry count passed in from `generate`). If
  `total == 0` returns `"No new content found."`. Otherwise it lists up to
  the first 5 section topics (appending `"...and {n} more"` when there are
  more than 5) and returns
  `f"{total} new items across {len(sections)} topics: {', '.join(names)}"`.
  **`total` is `total_entries` (the distinct-entry count), NOT the sum of the
  (capped) section counts** — see Contract Holes.

## Contract Holes

### Primary hole: the summary's item count double-counts multi-tag entries and is decoupled from `total_entries` (ARCH-49)

The public `generate` contract states that `total_entries` is "count of
accumulated entries" and that a "one-line summary is generated from the
sections", but it states **no relationship between the two**, and the two
quantities are computed from different sources and disagree in the default
(`group_by="tags"`) path:

- `total_entries = len(entries)` — the count of **distinct** accumulated
  entries (each entry counted once).
- The summary's `total = sum(s.count for s in sections)` — the sum of the
  **per-section** counts.

In `_group_by_tags`, an entry with `k` tags is appended to `k` different tag
buckets, so it is counted `k` times in `sum(s.count)`. Concretely:

- **Inflation:** an entry tagged `["a", "b"]` (and no other entries) yields
  two sections of one entry each, so the summary reads `"2 new items across 2
  topics: a, b"` while `total_entries` is `1`. The summary reports more items
  than the digest actually contains.
- **Deflation:** the per-section cap (`max_entries_per_section`, default 10)
  truncates each bucket independently, so `sum(s.count)` can also fall **below**
  `total_entries` when a single tag holds more than the cap (e.g. 15 entries
  all tagged `"a"` → one section of 10 → summary says `"10 new items"` while
  `total_entries` is `15`).

The `group_by="source"` path does not inflate (each entry lands in exactly one
bucket), but it still deflates under the cap, so the summary and
`total_entries` can disagree there too. Because the `generate` docstring and
this page make no promise that the summary's number equals `total_entries`, a
caller cannot tell from the contract that the headline "N new items" figure is
a per-section sum (double-counting multi-tag entries and capping per section)
rather than the distinct-entry count. This is the single most important hole:
the digest's headline number is silently wrong for the ordinary multi-tag
input in the default grouping, and the contract gives no way to know which of
the two counts is authoritative.

The fix is to make the relationship explicit (pick one and state it in the
`generate` docstring + this page): either (A) compute the summary's `total`
from the distinct-entry count (so it always equals `total_entries`), or (B)
document that the summary's number is the sum of the per-section (capped)
counts and therefore intentionally differs from `total_entries` in the
multi-tag / over-cap cases — and state which figure a caller should treat as
authoritative.

### Secondary notes (not ticketed)

- `group_by` is never validated: any string other than `"none"`/`"source"`
  (including a typo like `"tag"`) silently runs tag grouping.
- `period_start`/`period_end` are passed through verbatim when truthy and
  never parsed or validated; a malformed string is emitted unchanged.
- `format_markdown` applies no escaping to any field (title, url, summary,
  tags, H1 title), so Markdown-significant characters in an entry produce
  malformed output with no error (analogous to the content-exporter Markdown
  hole, but not ticketed here).
- `format_text` truncates `entry.summary` to 100 characters and omits tags
  entirely, whereas `format_markdown` emits the full summary and a `Tags:`
  line — the two renderers are not interchangeable views.
- `DigestEntry.to_dict` and `ContentDigest.to_dict` alias the `tags` list
  object (not a copy), so mutating the returned dict's `tags` mutates the
  live entry.
- Empty input is well-defined: `generate()` with no entries returns a digest
  with `sections=[]`, `total_entries=0`, and summary `"No new content found."`
  — a defined behavior, not a hole.
