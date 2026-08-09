# Implementation Plan: Link Preview Module

## Commit 1: Tests (tests/test_link_preview.py)
- Test `LinkPreview` dataclass defaults
- Test `LinkPreviewGenerator.generate()` with full OG tags
- Test `LinkPreviewGenerator.generate()` with partial OG tags
- Test `LinkPreviewGenerator.generate()` with Twitter Card tags
- Test fallback to standard meta tags (title, description)
- Test fallback to title tag when no OG title
- Test empty HTML returns empty preview
- Test og:image with relative URL gets resolved
- Test twitter:card type extraction
- Test og:locale extraction
- Test og:site_name extraction
- Test og:type extraction
- Test that og:title takes priority over <title> tag
- Test that og:description takes priority over meta description

## Commit 2: Implementation (personal_index/link_preview.py)
- `LinkPreview` dataclass with fields: title, description, image_url, site_name, type, url, twitter_card, locale
- `LinkPreviewGenerator` class with `generate(html, base_url)` method
- Internal helpers: _extract_og_tag, _extract_twitter_tag, _extract_meta, _extract_title
- Fallback chain for each field

## Commit 3: Integration (tests/test_link_preview_integration.py)
- Test integration with HTMLScraper: scraper extracts content, generator creates preview
- Test end-to-end with realistic HTML containing OG tags
- Test that LinkPreviewGenerator can work with ScrapedContent
