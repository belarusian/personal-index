# url_utils — URL helpers (spec)

`personal_index.url_utils` (411 lines) is a module of pure, stateless URL
helpers merged from the legacy `url_utils.py` and `url_normalizer.py`. Every
function takes a string (or a small list) and returns a string / bool / int /
list — there is no class, no I/O, and no shared state. The two module-level
constants are:

- `EXCLUDED_EXTENSIONS` — a `set[str]` of file extensions (`.jpg`, `.css`,
  `.js`, `.pdf`, …) that `is_excluded_url` treats as non-crawlable.
- `EXCLUDED_SCHEMES` — a `set[str]` of schemes (`javascript`, `mailto`,
  `data`, `tel`, `ftp`) that `is_excluded_url` treats as non-crawlable.

The public helpers are grouped below by concern. Each entry gives the
signature, the return contract, and the guard / early-return path.

## Validation & normalization

### `is_valid_url(url: str) -> bool`
True only when `url` is non-empty, parses, has scheme `http` or `https`, and
has a non-empty `netloc`. Empty string, a scheme-less string, and any
non-http/https scheme (`ftp://`, `javascript:`) all return `False`. A parse
failure (`ValueError`/`AttributeError`) returns `False`.

### `normalize_url(url, base_url="", remove_fragment=True, lowercase_path=True, remove_default_port=True, sort_query_params=True) -> str | None`
Applies standard URL transformations and returns the normalized string, or
`None` when `url` is empty or its scheme is not `http`/`https`.

- When `base_url` is given and `url` has no scheme, `url` is first resolved
  against `base_url` via `urljoin`.
- Each transformation is independently opt-out-able via its flag:
  `remove_fragment` (drop `#fragment`), `lowercase_path` (lowercase the path),
  `remove_default_port` (strip `:80`/`:443` for http/https), and
  `sort_query_params` (sort the query string alphabetically).
- **Guard path:** on a parse failure (`ValueError`/`AttributeError`) the
  ORIGINAL `url` is returned unchanged — not `None`. This is the one path that
  returns a non-normalized value.

### `is_canonical(url: str) -> bool`
True when `normalize_url(url) == url` — i.e. the URL is already in canonical
form. Because `normalize_url` returns `None` for non-http/https schemes, a
non-normalizable URL is never canonical (it compares `None == url`).

## Domain / host extraction

### `extract_domain(url: str) -> str | None`  (alias: `get_domain`)
Returns the lowercased host with the port stripped, or `None` when `url` is
empty, has no `netloc`, or fails to parse. Port-stripping is bracket-aware: a
leading `[` (IPv6 literal such as `[::1]` or `[2001:db8::1]:8080`) is cut at
the closing `]` so the internal colons are preserved; otherwise a trailing
`:port` is dropped with `rsplit(":", 1)`.

### `get_path(url: str) -> str`
`urlparse(url).path`, or `"/"` when the path is empty.

### `get_query_string(url: str) -> str`
`urlparse(url).query` (empty string when absent).

### `get_fragment(url: str) -> str`
`urlparse(url).fragment` (empty string when absent).

### `extract_subdomain(url: str) -> str`
Splits the domain on `.` and returns all labels except the last two, joined by
`.`. Returns `""` when the domain is empty or has two or fewer labels (no
subdomain).

### `get_tld(url: str) -> str`
**Returns only the LAST dot-label of the domain** (`domain.split(".")[-1]`),
or `""` when the domain is empty.

> **Contract hole (ARCH-61).** The docstring says "Extract top-level domain
> from URL" but the body returns `parts[-1]`, which is correct **only for
> single-label TLDs** (`com`, `org`, `net`). It is silently wrong for:
>
> - **two-label TLDs** — `get_tld('https://www.example.co.uk/x')` → `'uk'`
>   (the real TLD is `co.uk`); `get_tld('https://example.com.au')` → `'au'`
>   (real TLD `com.au`).
> - **dotless hosts** — `get_tld('https://intranet')` → `'intranet'` and
>   `get_tld('https://localhost:8080/x')` → `'localhost'`; a bare hostname has
>   **no TLD**, yet the whole host is returned as if it were one.
>
> Callers cannot tell from the docstring that multi-part TLDs and dotless
> hosts produce silently-wrong answers. See `tickets/ARCH-61.md` for the
> chosen resolution and the pinning tests.

### `get_url_depth(url: str) -> int`
Number of path segments: `urlparse(url).path.strip("/")` split on `/`, or `0`
when `url` is empty, the path is empty, or parsing fails.

## Comparison & classification

### `is_same_domain(url1: str, url2: str) -> bool`
`extract_domain(url1) == extract_domain(url2)`. Note both sides can be `None`,
so two empty / netloc-less URLs compare as "same domain".

### `is_internal_link(url: str, base_url: str) -> bool`
`is_same_domain(url, base_url)`.

### `urls_are_equivalent(url1: str, url2: str) -> bool`
True only when **both** normalize (via `normalize_url`) to the same
http/https URL. A URL that normalizes to `None` (non-http/https or empty) is
never equivalent to anything, so two distinct non-normalizable URLs are not
reported as equivalent.

### `is_robotstxt(url: str) -> bool`
True when the path (with trailing `/` stripped) equals `/robots.txt`.

### `is_sitemap(url: str) -> bool`
True when the path's basename (lowercased) starts with `sitemap` **and**
carries a file extension (a `.` in the basename). So `sitemap.xml`,
`sitemap_index.xml`, `sitemap-news.xml` are sitemaps; `/about-sitemap` and
`/sitemap-backup` (no extension) are not.

### `is_excluded_url(url: str) -> bool`
True when `url` is empty, its scheme is in `EXCLUDED_SCHEMES`, or its
lowercased path ends with any extension in `EXCLUDED_EXTENSIONS`.

## Query manipulation

### `remove_query_params(url: str, params: list | None = None) -> str`
Removes the named query parameters from `url`. When `params` is empty/`None`
the URL is returned unchanged (guard path). Each `&`-separated part whose key
(`part.split("=", 1)[0]`) is in `params` is dropped; the rest are re-joined.
On a parse failure the original URL is returned.

### `strip_tracking_params(url: str) -> str`
Removes a fixed set of tracking parameters (`utm_source`, `utm_medium`,
`utm_campaign`, `utm_term`, `utm_content`, `utm_id`, `fbclid`, `gclid`,
`mc_eid`, `igshid`) from the query string, preserving the rest.

## Path / filesystem

### `url_to_path(url: str) -> str`
Returns `""` for an empty URL. Otherwise `f"{netloc}_{safe}"` where `safe` is
the path (or `"index"` when the path is empty) with every character other than
`[a-zA-Z0-9_-]` replaced by `_`.

## Joining & resolution

### `join_urls(base: str, relative: str) -> str`
- If `relative` has an `http`/`https` scheme it is returned as-is.
- If `relative` starts with `/` it replaces the base path entirely.
- Otherwise the base path is treated as a directory (a trailing `/` is added
  when absent) and `relative` is appended.

### `resolve_relative_url(base_url: str, relative_url: str) -> str | None`
Resolves `relative_url` against `base_url`.
- Returns `None` when `relative_url` has a scheme other than `http`/`https`
  (rejects `javascript:`, `mailto:`, …).
- Returns `relative_url` as-is when it has an `http`/`https` scheme.
- When it has a `netloc`, the base scheme is combined with the relative
  netloc/path/query/fragment.
- For a relative path, the path is resolved (absolute paths used directly;
  fragment-only / query-only references point at the base page; otherwise the
  base path's directory is used) and normalized with `posixpath.normpath` to
  collapse `..` and `.`.

## Extraction

### `extract_all_urls(html: str, base_url: str = "") -> list`
Extracts URLs from HTML (via BeautifulSoup `<a href>` when available) or, as a
fallback, from plain text via regex (`https?://[^\s<>"')\]]+`). Each candidate
is normalized with `normalize_url` and kept only when it is a valid http/https
URL; `#`- and `javascript:`-prefixed hrefs are skipped. Returns a list of
normalized URL strings (possibly empty).
