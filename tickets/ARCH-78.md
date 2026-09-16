# ARCH-78 — link_preview: `LinkPreviewGenerator.generate` drops `base_url` for the canonical `url` field (no `og:url` → `url == ""`)

Status: CLAIMED 2026-09-16
Component: `personal_index/link_preview.py` — `LinkPreviewGenerator.generate` (lines 48-67); specifically the `for field in ("site_name", "type", "url", "locale")` loop (line 64) that reads `url` only from `og:url`; contrast `_resolve_image_url` (line 120) which DOES honor `base_url` for `image_url`.
Umbrella: ARCH-2 (#983)
Issue: #1430
Docs: `docs/link_preview.md` (Contract hole, ARCH-78)

## Problem
`generate(self, html, base_url="")` accepts a `base_url` argument and uses it to
resolve `image_url` via `urljoin` (line 61 → `_resolve_image_url`, line 120).
But the canonical `url` field is populated **only** from `og:url` (line 64)
with **no fallback to `base_url`**. So when the HTML has no `og:url` tag,
`preview.url` is `""` even though the caller explicitly supplied the URL they
are previewing — the `base_url` is silently dropped for the one field that most
naturally should carry it.

The asymmetry is the hole: `base_url` is honored for `image_url` but not for
`url`. Verified (cycle 246):

    g = LinkPreviewGenerator()
    html = '<html><head><title>T</title></head></html>'   # no og:url
    g.generate(html, "http://example.com/page").url       # -> ""  (base_url dropped)
    # with an og:image, base_url IS used for image_url but NOT for url:
    g.generate('<html><head><meta property="og:image" content="/i.png"></head></html>',
               "http://example.com/page").url             # -> ""  (still dropped)
    g.generate('<html><head><meta property="og:image" content="/i.png"></head></html>',
               "http://example.com/page").image_url       # -> "http://example.com/i.png"

This is surprising/lossy where a caller would reasonably expect the canonical
`url` to reflect the URL they passed in. No existing test pins the
og:url-absent + base_url-given → `url == ""` case (the deep-test docstring line
17 "site_name/type/url/locale: og:* only" merely *describes* the current
behavior; it does not assert `url` *should* be empty when `base_url` is given).

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

## Public contract (recommended)
`generate(self, html: str, base_url: str = "") -> LinkPreview`:
- `html` falsy: return an empty `LinkPreview()` (unchanged).
- `title`, `description`, `image_url`, `site_name`, `type`, `locale`,
  `twitter_card`: unchanged (their chains are correct).
- `url`: read from `og:url` **first**; when `og:url` is absent/empty, fall back
  to `base_url` (the URL the caller is previewing). So
  `generate(html_without_og_url, "http://example.com/page").url` ->
  `"http://example.com/page"`. When both `og:url` and `base_url` are empty,
  `url` stays `""` (unchanged).
  (Alternative acceptable contract: keep `url` `og:*`-only but document the
  asymmetry explicitly in the `generate` docstring so a caller is not surprised
  that `base_url` is dropped for `url`. The implementer picks ONE and the
  `generate` docstring must state it exactly.)

## Acceptance criteria
1. `generate` with HTML that has **no** `og:url` and a non-empty `base_url`
   returns `preview.url == base_url` (the recommended fallback contract) — it
   does not return `""` silently. (Or, if the documented-asymmetry contract is
   chosen, the `generate` docstring states that `base_url` is not used for
   `url`.)
2. `generate` with HTML that **has** `og:url` returns `preview.url == og:url`
   value regardless of `base_url` (og:url wins; existing
   `test_full_og_tags` / deep `test_round_trip_all_fields` stay green).
3. `generate` with no `og:url` and empty `base_url` returns `preview.url == ""`
   (unchanged; existing `test_default_values` stays green).
4. `image_url` resolution is unchanged: `og:image`/`twitter:image` resolved via
   `urljoin(base_url, ...)` (existing urljoin tests stay green).
5. `title`, `description`, `site_name`, `type`, `locale`, `twitter_card` are
   unchanged (existing tests stay green).

## Pinning tests to add (tests/test_link_preview.py)
- **The hole (og:url absent + base_url given):**
  `generate('<html><head><title>T</title></head></html>',
  "http://example.com/page")` — assert `preview.url == "http://example.com/page"`
  (recommended fallback contract), NOT `""`. Pins the corrected behavior against
  the returned object, not the docstring.
- **Guard path (og:url absent + base_url empty):**
  `generate('<html><head><title>T</title></head></html>', "")` — assert
  `preview.url == ""`. Pins the both-empty branch so the fallback does not
  over-reach.
- **Normal case (og:url present, base_url given):**
  `generate('<html><head><meta property="og:url" content="http://u.com/x"></head></html>',
  "http://example.com/page")` — assert `preview.url == "http://u.com/x"` (og:url
  wins over base_url). Confirms the fallback is not over-broad.

## Docs (SAME PR)
`docs/link_preview.md` (new, spec) + the `link-preview.md` index entry in
docs/README.md ship in the same PR as this ticket.
