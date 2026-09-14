# ARCH-51: `_is_valid_url` accepts scheme-prefixed strings with no host

**Status:** VERIFIED (cycle 217, validator) — pinning + adversarial tests pass on main 6d1ed09 [was IMPLEMENTED #1318@7c9bf86 (cycle 255)]
**Component:** `personal_index/content_validation.py`
**Umbrella:** ARCH-2 (#983)
**Docs:** `docs/content-validation.md`

## Problem

`ContentValidator._is_valid_url(url)` only checks `url.startswith(("http://", "https://"))`. It does not verify that the URL has a non-empty host. Consequently a content item with `url="http://"` (no host), `"https://"` (no host), or `"http:// "` (trailing space, no host) passes `validate` / `validate_single` and is reported valid. Because `url` is a default required field, this is the module's most impactful false-negative: malformed URLs are accepted by the core validation path.

## Contract

Change `_is_valid_url` to require a non-empty host: