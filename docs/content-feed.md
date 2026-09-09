# Content feed (`personal_index.content_feed`)

Status: **spec** — audited against current code (cycle 217).

RSS 2.0 / Atom 1.0 feed generation for recent saves. Stdlib-only (`html`,
`dataclasses`, `datetime`, `enum`). Three public types: `FeedFormat` (enum),
`FeedItem` (dataclass), `FeedGenerator` (dataclass).

## FeedFormat
`class FeedFormat(str, Enum)` — two members: `RSS = "rss"`, `ATOM = "atom"`.
Because it subclasses `str`, a member compares equal to its string value
(`FeedFormat.RSS == "rss"`).

## FeedItem
`@dataclass` with fields: `title: str`, `link: str`, `id: str = ""`,
`description: str = ""`, `author: str = ""`,
`categories: list[str] = field(default_factory=list)`,
`published: datetime | None = None`, `updated: datetime | None = None`.

- `__post_init__()` — fills defaults AFTER init: if `id` is falsy it is set to
  `link`; if `published` is falsy it is set to `datetime.now(timezone.utc)`;
  if `updated` is falsy it is set to `published` (so `updated` always tracks
  `published` unless the caller supplies both).
- `to_dict() -> dict` — returns a NEW dict with exactly eight keys: `title`,
  `link`, `id`, `description`, `author`, `categories` (a COPY of the list via
  `list(self.categories)`), `published` (ISO-8601 string, or `None`),
  `updated` (ISO-8601 string, or `None`). No guard path; no side effects.
- `from_dict(cls, data: dict) -> FeedItem` (classmethod) — reads each key with
  a default (`title`/`link`/`id`/`description`/`author` default to `""`,
  `categories` to `[]`). `published`/`updated` are parsed from ISO-8601 strings
  via `datetime.fromisoformat`; **guard path:** a non-string, empty, or
  unparseable value yields `None` (the `ValueError` is swallowed), and `None`
  then re-triggers the `__post_init__` default (now-UTC / published).

## FeedGenerator
`@dataclass` with fields: `title: str`, `link: str`, `description: str = ""`,
`items: list[FeedItem] = field(default_factory=list)`, `language: str =
"en-us"`, `ttl: int = 60`, `generator: str = "personal-index"`,
`max_items: int = 100`, `feed_id: str = ""`.

- `__post_init__()` — if `feed_id` is falsy it is set to `link`.
- `add_item(item: FeedItem) -> None` — appends `item`, then sorts `items` by
  `published` newest-first (a `None` published sorts as
  `datetime.min.replace(tzinfo=timezone.utc)`, i.e. oldest), then truncates to
  `max_items` (the OLDEST items are dropped). So `add_item` is the ONLY path
  that enforces the cap and ordering.
- `add_items(items: list[FeedItem]) -> None` — calls `add_item` per item (so
  the sort + cap run after EACH item, not once at the end).
- `clear() -> None` — empties `items` in place.
- `get_feed_type(fmt: FeedFormat) -> str` — returns `"application/rss+xml"`
  for `FeedFormat.RSS`, else `"application/atom+xml"`.
- `generate(fmt: FeedFormat = FeedFormat.RSS) -> str` — dispatches to
  `_generate_rss()` or `_generate_atom()`; returns the full XML document as a
  single string (lines joined by `\n`).
- `to_dict() -> dict` — returns a NEW dict with exactly SEVEN keys: `title`,
  `link`, `description`, `language`, `ttl`, `generator`, `items` (each item
  via `FeedItem.to_dict`). **It does NOT include `max_items` or `feed_id`.**
- `from_dict(cls, data: dict) -> FeedGenerator` (classmethod) — reads
  `title`/`link`/`description`/`language`/`ttl`/`generator` (defaults
  `""`/`""`/`""`/`"en-us"`/`60`/`"personal-index"`) and `items` (each via
  `FeedItem.from_dict`), then assigns `gen.items = items` directly (bypassing
  `add_item`, so no re-sort/cap on load). **It does NOT read `max_items` or
  `feed_id`** — both fall back to their dataclass defaults (`100` and, via
  `__post_init__`, `link`).

### Private helpers (documented for completeness; not part of the public API)
- `_escape(text: str) -> str` — `html.escape(text, quote=True)`.
- `_format_rss_date(dt: datetime | None) -> str` — RFC-822-ish
  `"%a, %d %b %Y %H:%M:%S %z"`; a `None` dt is formatted from
  `datetime.now(timezone.utc)`.
- `_format_atom_date(dt: datetime | None) -> str` — ISO-8601; a `None` dt is
  formatted from `datetime.now(timezone.utc)`.
- `_generate_rss() -> str` — RSS 2.0: `<rss version="2.0">` + `<channel>` with
  `title`/`link`/`description`/`language`/`ttl`/`generator`/`lastBuildDate`
  (now-UTC), then one `<item>` per entry (`title`/`link`/`guid`=id, and
  `description`/`author`/`category`/`pubDate` only when present).
- `_generate_atom() -> str` — Atom 1.0: `<feed xmlns=".../Atom">` with
  `title`/`link rel="self"`/`id`=feed_id/`updated`(now-UTC)/`generator`,
  `subtitle` only when `description` is set, then one `<entry>` per item
  (`title`/`link`/`id`/`updated`, and `published`/`summary`/`author`/
  `category` only when present).

## Contract holes
- **`to_dict`/`from_dict` is a lossy round-trip for `FeedGenerator`:**
  `to_dict()` omits `max_items` and `feed_id`, and `from_dict()` does not
  restore them, so a `FeedGenerator(max_items=10, feed_id="custom")`
  round-trips to `max_items=100, feed_id=link`. The item cap silently resets to
  the default and the Atom `<id>` identity silently changes (ARCH-54).
