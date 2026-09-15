# link_preview — `personal_index.link_preview`

Spec page (matches CURRENT code as of cycle 246).

`link_preview.py` generates Open Graph / Twitter Card preview cards from HTML.
It exposes two public types: the `LinkPreview` dataclass (a single structured
card) and the `LinkPreviewGenerator` (the HTML → card extractor).

> **Near-name disambiguation:** this page documents
> `personal_index/link_preview.py` (`LinkPreview` / `LinkPreviewGenerator`).
> It is NOT `personal_index/link_analyzer.py` (`LinkAnalyzer`, covered by
> `link-analyzer.md`) and NOT the `personal_index/content_linker` subpackage.
> Tests import `from personal_index.link_preview import LinkPreview,
> LinkPreviewGenerator`.

## `LinkPreview` (dataclass, line 19)

Eight `str` fields, all defaulting to `""` (in declaration order): `title`,
`description`, `image_url`, `site_name`, `type`, `url`, `twitter_card`,
`locale`. No `__post_init__`, no `to_dict`/`from_dict` — it is a plain
dataclass used only as the return value of `generate`.

## `LinkPreviewGenerator` (line 36)

- `generate(self, html: str, base_url: str = "") -> LinkPreview` (line 48):
  - **Guard:** if `html` is falsy (`""` or `None`), returns an empty
    `LinkPreview()` immediately (all fields `""`) — no parsing (line 50).
  - Otherwise parses with `BeautifulSoup(html, "html.parser")` and fills each
    field via the priority chains below.
  - `title` (line 55): `og:title` > `twitter:title` > the `<title>` element
    text.
  - `description` (line 60): `og:description` > `twitter:description` >
    standard `<meta name="description">` (via `_fallback_chain`).
  - `image_url` (line 61): `og:image` > `twitter:image` (via `_og_or_twitter`),
    then **resolved against `base_url`** via `_resolve_image_url` (urljoin).
  - `site_name`, `type`, `url`, `locale` (line 64): each is read **only** from
    its `og:*` tag (`og:site_name`, `og:type`, `og:url`, `og:locale`) via a
    single `setattr` loop. There is **no fallback** for any of these four —
    in particular `url` has **no fallback to `base_url`** (see Contract hole).
  - `twitter_card` (line 66): read **only** from `twitter:card`.

### Private helpers

- `_fallback_chain(self, soup, meta_name, og_name, tw_name) -> str` (line 69):
  returns `og` > `twitter` > standard-meta, first truthy value.
- `_og_or_twitter(self, soup, name) -> str` (line 79): returns `og:<name>` >
  `twitter:<name>`, first truthy value.
- `_extract_og_tag(self, soup, property_name) -> str` (line 83): finds
  `<meta property=...>`, returns `content.strip()` (or `""` when the tag is
  absent or `content` is falsy).
- `_extract_twitter_tag(self, soup, name) -> str` (line 93): same, for
  `<meta name=...>`.
- `_extract_meta(self, soup, name) -> str` (line 103): same, for a standard
  `<meta name=...>`.
- `_extract_title_tag(self, soup) -> str` (line 113): returns
  `<title>.string.strip()` (or `""` when absent/empty). Note `<title>` is
  RCDATA, so nested markup inside it is literal text, not parsed.
- `_resolve_image_url(self, image_url, base_url) -> str` (line 120): returns
  `""` when `image_url` is empty; returns `image_url` unchanged when
  `base_url` is empty; otherwise `urljoin(base_url, image_url)`.

## Persistence
None. `LinkPreviewGenerator` is stateless and in-memory; there is no
serialization, no file I/O, and no `save`/`load`.

## Contract hole (ARCH-78)
`generate` accepts a `base_url` argument and uses it to resolve `image_url`
(via `urljoin`), but the canonical `url` field is populated **only** from
`og:url` (line 64) with **no fallback to `base_url`**. So when the HTML has no
`og:url` tag, `preview.url` is `""` even though the caller explicitly supplied
the URL they are previewing — the `base_url` is silently dropped for the one
field that most naturally should carry it. Verified (cycle 246):

    g = LinkPreviewGenerator()
    html = '<html><head><title>T</title></head></html>'   # no og:url
    g.generate(html, "http://example.com/page").url       # -> ""  (base_url dropped)
    g.generate(html, "http://example.com/page").image_url # -> ""  (no og:image either)
    # with an og:image, base_url IS used for image_url but NOT for url:
    g.generate('<html><head><meta property="og:image" content="/i.png"></head></html>',
               "http://example.com/page").url             # -> ""  (still dropped)
    g.generate('<html><head><meta property="og:image" content="/i.png"></head></html>',
               "http://example.com/page").image_url       # -> "http://example.com/i.png"

The asymmetry is the hole: `base_url` is honored for `image_url` but not for
`url`. See `tickets/ARCH-78.md`.

## What is NOT a hole (do not re-ticket)
- `title` (og > twitter > `<title>`), `description` (og > twitter >
  standard-meta), and `image_url` (og > twitter, urljoin-resolved) all have
  complete, correct fallback chains and are fully pinned by
  `tests/test_link_preview.py` and `tests/deep/test_link_preview_adversarial.py`.
- `site_name`, `type`, and `locale` are legitimately `og:*`-only: `base_url`
  cannot help populate them, so their lack of a fallback is not a hole.
- `twitter_card` is legitimately `twitter:card`-only.
- The empty/`None`-`html` guard (returns an empty card) and the `.strip()` of
  every extracted value are correct and pinned.
