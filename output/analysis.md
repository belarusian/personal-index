# Analysis: Link Preview Module

## Existing Codebase
- `personal_index/` package with many modules (scraper, content_extractor, etc.)
- Tests live in `tests/` directory, using pytest
- Uses `dataclass` patterns, `BeautifulSoup` for HTML parsing
- `scraper.py` already extracts OG tags as fallback for title/description
- `content_extractor.py` also extracts og:title

## What's Needed
A `link_preview` module that:
1. Parses HTML to extract Open Graph (og:*) meta tags
2. Parses Twitter Card meta tags
3. Generates structured preview cards with title, description, image, type, site_name
4. Falls back to standard meta tags when OG tags are missing
5. Provides a clean dataclass for the preview card

## Design
- `LinkPreview` dataclass: holds title, description, image_url, site_name, type, url, twitter_card
- `LinkPreviewGenerator` class: takes HTML + base_url, extracts OG/Twitter tags, returns LinkPreview
- Fallback chain: og:title > title tag > empty; og:description > meta description > empty; etc.
- Tests first, then implementation, then integration with scraper
