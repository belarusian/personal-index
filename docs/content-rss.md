# Content RSS (spec)

`personal_index.rss` — the "crawl" stage's feed-parsing component of the
crawl→filter→score→tag→index pipeline. Given a raw XML string (and an optional
feed URL), it parses RSS 2.0 **and** Atom feeds with `defusedxml` and returns a
structured `Feed` (title, link, description, author, entries, feed_url) whose
entries are `FeedEntry` objects (title, link, summary, content, author,
published, updated, categories, guid). It does **no network I/O** — fetching
the feed bytes is the pipeline's job; the parser only parses.

The module exports three names: `FeedEntry`, `Feed`, `RSSParser`.

## Public API

### `FeedEntry` (dataclass)
A single entry from an RSS/Atom feed. Fields, in order:
- `title: str = ""` — entry title.
- `link: str = ""` — entry link (RSS `<link>`; Atom `<link href>`).
- `summary: str = ""` — RSS `<description>`; Atom `<summary>`.
- `content: str = ""` — RSS `content:encoded` (namespaced or plain); Atom
  `<content>`.
- `author: str = ""` — RSS `<author>` (or `dc:creator` fallback); Atom
  `<author><name>`.
- `published: str | None = None` — RSS `<pubDate>`; Atom `<published>`.
  `None` when absent (not `""`).
- `updated: str | None = None` — **Atom only** (`<updated>`). RSS items never
  populate this field, so it stays `None` for every RSS entry (see contract
  hole 2).
- `categories: list[str] = []` — RSS `<category>` text; Atom `<category term>`.
- `guid: str = ""` — RSS `<guid>`; Atom `<id>`. Falls back to `entry.link`
  when the guid/id element is absent or empty (so `guid` can be `""` when the
  entry has no link either).

`to_dict() -> dict` returns all nine fields as a plain dict (same key names).

### `Feed` (dataclass)
A parsed RSS/Atom feed. Fields, in order:
- `title: str = ""` — feed title (RSS `<channel><title>`; Atom `<title>`).
- `link: str = ""` — feed link (RSS `<channel><link>`; Atom `<link href>`).
- `description: str = ""` — RSS `<channel><description>`; Atom `<subtitle>`.
- `author: str = ""` — RSS `<channel><managingEditor>` (or `<author>`
  fallback); Atom `<author><name>`.
- `entries: list[FeedEntry] = []` — the parsed entries, in document order.
- `feed_url: str = ""` — the `feed_url` passed to `parse` (echoed verbatim).

- `entry_count -> int` (property) — `len(self.entries)`.
- `get_recent_entries(count: int = 10) -> list[FeedEntry]` — returns
  `self.entries[:count]`. **Guard path:** `count=0` returns `[]`.
  **Contract hole:** a negative `count` leaks Python negative-slice semantics
  (`entries[:-1]` = all-but-last) instead of `[]` — the same class as
  **ARCH-17** (see `docs/CONTRACTS.md`); not re-ticketed here.

### `RSSParser`
Stateless parser (no instance state beyond the `ATOM_NS` class constant
`"http://www.w3.org/2005/Atom"`).

- `parse(xml_content: str, feed_url: str = "") -> Feed`
  - **Guard path 1:** empty `xml_content` (`""` / falsy) → returns an empty
    `Feed(feed_url=feed_url)` (no entries, no title).
  - **Guard path 2:** XML that fails to parse (`defusedxml` `ParseError`) →
    returns an empty `Feed(feed_url=feed_url)`.
  - Otherwise: parses the root, strips any namespace prefix from the root tag
    (splits on `}`), and dispatches on the bare root tag name:
    - `"rss"` → `_parse_rss`
    - `"feed"` → `_parse_atom`
    - **any other root tag** (e.g. `<html>`, `<rdf:RDF>`, `<atom>`) → returns
      the empty `Feed(feed_url=feed_url)` with **no signal** that the input
      was not a feed (see contract hole 1).
  - `feed.feed_url` is set to `feed_url` on the returned object in all paths.

- `is_feed(xml_content: str) -> bool` (static)
  - **Guard path:** empty `xml_content` → `False`.
  - Otherwise: `True` if any of the regexes `<rss`, `<feed`, `<channel`,
    `xmlns.*atom`, `xmlns.*rss` matches the **first 500 characters**
    (case-insensitive). See contract hole 3 for the 500-char window.

### Private methods (documented for contract completeness)
- `_parse_rss(root, feed_url) -> Feed` — reads `<channel>` (if absent, returns
  an empty `Feed`); channel title/link/description; author from
  `managingEditor` then `author`; one `_parse_rss_item` per `<item>`.
- `_parse_rss_item(item) -> FeedEntry` — title, link, `description`→summary,
  `content:encoded` (namespaced `{http://purl.org/rss/1.0/modules/content/}encoded`
  then plain `content:encoded`)→content, `author` (then `dc:creator`)→author,
  `pubDate`→published, `guid` (fallback to link)→guid, `<category>` text→
  categories. **Never sets `updated`.**
- `_parse_atom(root, feed_url) -> Feed` — title (`atom:title` then `title`),
  link (`atom:link[@rel='alternate']`, else first link with `rel='alternate'`
  or no `rel`), subtitle→description, author (`atom:author/atom:name`), one
  `_parse_atom_entry` per `atom:entry`.
- `_parse_atom_entry(entry_elem, ns) -> FeedEntry` — title, alternate link,
  summary, content, author, published, updated, guid (`atom:id` then `id`,
  fallback to link), `atom:category` `term`→categories.
- `_atom_find_fallback(parent, tag, ns)` / `_atom_text(parent, tag, ns)` /
  `_atom_text_or_none(parent, tag, ns)` — namespace-prefixed lookup with a
  plain-tag fallback; `_atom_text` returns `""` when absent,
  `_atom_text_or_none` returns `None` when absent.
- `_find_atom_link(parent, ns)` — the alternate link element (see above).

## Invariants
- `parse` never raises on malformed or non-feed input — every failure path
  returns an (empty) `Feed`. The only way to know the input was not a feed is
  to call `is_feed` first (see contract hole 1).
- `FeedEntry.to_dict()` keys are exactly the nine dataclass field names.
- `entry_count == len(entries)` always.
- `published`/`updated` are `None` (not `""`) when the source element is
  absent or empty.

## Side effects
None. The parser is pure: it reads the input string and returns new
`Feed`/`FeedEntry` objects. No I/O, no mutation of shared state, no logging.

## Contract holes

1. **Silent empty feed for non-feed root tags:** `parse` returns an empty
   `Feed` (no entries, no title) when the root tag is neither `rss` nor
   `feed` (e.g. `<html>`, `<rdf:RDF>`, `<atom>`), with no exception, flag, or
   other signal. A caller cannot distinguish "a valid feed with zero entries"
   from "this was not a feed at all". `is_feed` exists precisely to pre-check,
   but `parse` neither calls it nor records that the dispatch fell through.
   → **ARCH-21** (ticketed).

2. **RSS entries never populate `updated`:** `_parse_rss_item` sets
   `published` (from `<pubDate>`) but never `updated`, so every RSS entry has
   `updated=None` while Atom entries may carry a value. RSS 2.0 has no standard
   "updated" element, so this is arguably by-design, but the `FeedEntry`
   docstring does not state the asymmetry, so a reader who expects `updated`
   to be populated for RSS is surprised.

3. **`is_feed` only inspects the first 500 characters:** the regexes run over
   `xml_content[:500]`, so a feed whose `<rss`/`<feed`/`<channel` tag or
   `xmlns` declaration appears after character 500 (e.g. a long XML prolog or
   leading comment) is misclassified as "not a feed". The window is a
   reasonable heuristic but is undocumented.

4. **`guid` can be an empty string:** when the guid/id element is absent or
   empty, `guid` falls back to `entry.link`, which is itself `""` when the
   entry has no link. So `guid` is not guaranteed to be a non-empty unique
   identifier — a downstream dedup key built on `guid` sees `""` for such
   entries.
