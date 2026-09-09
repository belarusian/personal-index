# ARCH-31: url_classifier — /static/ and /assets/ overlap makes MEDIA_PATTERNS entries dead

Status: VERIFIED (validator cycle 160: 29 pinning tests pass + adversarial - /static/photo.jpg and /assets/img.png -> STATIC 0.9 (STATIC wins over media ext), case-insensitive STATIC/ASSETS -> STATIC, photo.jpg and images/photo.jpg -> MEDIA 0.85, nested a/static/b/x.png -> STATIC; MEDIA_PATTERNS clean of /static/ /assets/)
Component: `personal_index/url_classifier.py`
Issue: #1087
Refs: ARCH-2 (#983 umbrella)

## Symptom

`/static/` and `/assets/` appear in **both** `MEDIA_PATTERNS` and
`STATIC_PATTERNS`. Because the rule order checks STATIC (position 4) before
MEDIA (position 5), any URL containing `/static/` or `/assets/` is always
classified STATIC — the two MEDIA_PATTERNS entries can never fire.

Example: `classify("https://example.com/static/logo.png")` returns
`category=STATIC, confidence=0.9`, not MEDIA.

## Evidence

- `personal_index/url_classifier.py` line ~62: `r"/static/"` in MEDIA_PATTERNS
- `personal_index/url_classifier.py` line ~76: `r"/static/"` in STATIC_PATTERNS
- `personal_index/url_classifier.py` line ~63: `r"/assets/"` in MEDIA_PATTERNS
- `personal_index/url_classifier.py` line ~77: `r"/assets/"` in STATIC_PATTERNS
- Rule order in `classify()`: STATIC (idx 3) before MEDIA (idx 4)

## Minimal additive fix

Remove `r"/static/"` and `r"/assets/"` from `MEDIA_PATTERNS` (they are dead —
STATIC always wins). Alternatively, if the intent is that `/static/` with a
media extension SHOULD be MEDIA, reorder MEDIA before STATIC and remove the
duplicates from STATIC_PATTERNS. The contract decision is:

**Decision**: `/static/` and `/assets/` are STATIC (they are asset-serving
paths). Remove them from MEDIA_PATTERNS. The media-extension patterns
(`\.(jpg|png|...)`) in MEDIA_PATTERNS still catch media files that are NOT
under `/static/` or `/assets/` (e.g. `/images/photo.jpg` → MEDIA via
`/images/`, or `/downloads/photo.jpg` → DOCUMENT via `/downloads/` — the
extension pattern is a secondary signal).

Wait — actually `/images/` is in MEDIA_PATTERNS and is checked at MEDIA
position. A URL like `https://example.com/images/photo.jpg` matches `/images/`
at MEDIA position (5), but does it match anything earlier? No — not REDIRECT,
FEED, API, or STATIC. So it correctly lands MEDIA. Good.

The fix is simply: remove the two dead entries from MEDIA_PATTERNS.

## Acceptance criteria

1. `classify("https://example.com/static/logo.png")` → STATIC, 0.9 (unchanged).
2. `classify("https://example.com/assets/app.js")` → STATIC, 0.9 (unchanged).
3. `classify("https://example.com/images/photo.jpg")` → MEDIA, 0.85 (unchanged).
4. MEDIA_PATTERNS no longer contains `/static/` or `/assets/`.
5. No behavior change for any URL that was previously classified correctly.

## Pinning tests to add