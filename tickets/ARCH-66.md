# ARCH-66 — content_type: `.svg` is in both `TEXT_EXTENSIONS` and `MEDIA_EXTENSIONS`, so it is always classified `text` (never `image`) and is indexable

Status: IMPLEMENTED #1768@37ed382003517ee42411d7e49e872b54274d78fb on main (37ed382003517ee42411d7e49e872b54274d78fb)
Component: `personal_index/content_type.py` — `TEXT_EXTENSIONS` (line 53), `MEDIA_EXTENSIONS` (line 64), `_classify_category_from_ext` (lines 146-160)
Umbrella: ARCH-2 (#983)
Issue: #1380
Related: ARCH-31 (url_classifier `/static/`+`/assets/` overlap) — same "duplicate membership, first-check-wins, dead entry" class
Docs: `docs/content_type.md` (Contract Holes #1)

## Architect decision (cycle 281): Option 1 is authoritative
`docs/content_type.md` (Contract Holes #1) now states the authoritative
decision: **Option 1** — remove `.svg` from `TEXT_EXTENSIONS` (keep it in
`MEDIA_EXTENSIONS` + the image subset), so `.svg` classifies as `image` and
`should_index` returns `False`. Option 2 is rejected. The validator's deep test
`tests/deep/test_content_type_adversarial.py::TestDetectFromExtension::
test_svg_dual_membership_resolves_to_text` currently pins the OLD dual
membership + `text` resolution and must be updated to Option 1 (IMPL-11). That
is a `tests/deep/**` change the architect cannot make, so this ticket stays
OPEN-PUSHBACK for the validator; the docs/decision half is done.

## Problem
`.svg` is listed in **both** `TEXT_EXTENSIONS` (line 53) and
`MEDIA_EXTENSIONS` (line 64). `_classify_category_from_ext` checks the four
extension sets **in order** — `TEXT_EXTENSIONS` (line 146) before
`MEDIA_EXTENSIONS` (line 151) — so any `.svg` input is classified as `text`
before the media branch is ever reached. The `MEDIA_EXTENSIONS` entry for
`.svg` is **dead**: it can never fire.

Consequences (verified against the code):
- `detect_from_extension(".svg")` → `category == "text"`, `is_text == True`,
  `is_media == False`, `mime_type == "text/plain"` (never `image`).
- `should_index("https://example.com/logo.svg")` → `True` (an SVG image is
  treated as indexable text).

A reader of `MEDIA_EXTENSIONS` (and of the image subset at line 153, which
explicitly lists `.svg`) would expect `.svg` to be `image`; the actual result
is `text`. This is a silent priority trap, the same class as the
`/static/`+`/assets/` overlap in `url_classifier` (ARCH-31).

## Public contract (target)
`.svg` must classify as **`image`**, matching its presence in the
`MEDIA_EXTENSIONS` image subset (line 153). The `TEXT_EXTENSIONS` entry for
`.svg` is the anomaly (a copy-paste artifact) and must be removed so the
`MEDIA_EXTENSIONS` branch is reachable.

Preferred option (remove `.svg` from `TEXT_EXTENSIONS`):
1. Delete `".svg"` from `TEXT_EXTENSIONS` (line 53). Leave it in
   `MEDIA_EXTENSIONS` (line 64) and in the image subset (line 153).
   Result: `detect_from_extension(".svg")` → `category == "image"`,
   `is_media == True`, `is_text == False`, `mime_type == "image/svg+xml"`
   (from `mimetypes.guess_type("file.svg")`). `should_index("…/logo.svg")`
   → `False` (images are not indexed).

Alternative option (remove `.svg` from `MEDIA_EXTENSIONS`):
2. Delete `".svg"` from `MEDIA_EXTENSIONS` (line 64) and from the image
   subset (line 153). Leave it in `TEXT_EXTENSIONS`.
   Result: `.svg` stays `text`/indexable. This is the status quo made
   explicit, but it contradicts the image subset and the semantic meaning of
   SVG (a vector image).

Option 1 is preferred: it makes the classification match the module's own
image-subset intent and removes the dead entry. The normal paths for all other
extensions must be unchanged (e.g. `.txt` → `text`, `.mp4` → `media`,
`.pdf` → `document`).

## Behavior
- `detect_from_extension(".svg")` → option 1: `category == "image"`,
  `is_media is True`, `is_text is False`, `mime_type == "image/svg+xml"`;
  option 2: `category == "text"`, `is_text is True`, `is_media is False`.
- `should_index("https://example.com/logo.svg")` → option 1: `False`;
  option 2: `True`.
- `detect_from_extension(".txt")` → `category == "text"` (regression guard,
  unchanged).
- `detect_from_extension(".mp4")` → `category == "media"`, `is_media is True`
  (regression guard, unchanged).
- `detect_from_extension(".pdf")` → `category == "document"` (regression
  guard, unchanged).

## Guard inputs
- `detect_from_extension(".svg")` → the pinned classification above (the
  dual-membership input that currently resolves to `text`).
- `detect_from_extension(".txt")` → `text` (a genuine text extension,
  regression guard).
- `detect_from_extension(".mp4")` → `media` (a genuine media extension,
  regression guard).

## Acceptance criteria
1. `detect_from_extension(".svg")` → the chosen behavior pinned (option 1:
   `category == "image"`, `is_media is True`, `is_text is False`,
   `mime_type == "image/svg+xml"`; option 2: `category == "text"`,
   `is_text is True`, `is_media is False`).
2. `should_index("https://example.com/logo.svg")` → the chosen behavior
   pinned (option 1: `False`; option 2: `True`).
3. `detect_from_extension(".txt")` → `category == "text"` (regression guard:
   a genuine text extension is unchanged).
4. `detect_from_extension(".mp4")` → `category == "media"`, `is_media is True`
   (regression guard: a genuine media extension is unchanged).
5. `detect_from_extension(".pdf")` → `category == "document"` (regression
   guard: a genuine document extension is unchanged).

## Pinning tests to add
- `test_svg_classified_image` (option 1) / `test_svg_classified_text`
  (option 2): `ContentTypeDetector().detect_from_extension(".svg")` pins the
  chosen `category` / `is_text` / `is_media` / `mime_type`.
- `test_svg_should_index` (option 1) / `test_svg_should_index_text`
  (option 2): `ContentTypeDetector().should_index("https://example.com/logo.svg")`
  pins the chosen bool.
- `test_text_extension_regression`: `detect_from_extension(".txt")` →
  `category == "text"`, `is_text is True`.
- `test_media_extension_regression`: `detect_from_extension(".mp4")` →
  `category == "media"`, `is_media is True`.
- `test_document_extension_regression`: `detect_from_extension(".pdf")` →
  `category == "document"`, `is_document is True`.

## Docs update (same PR)
`docs/content_type.md` — Contract Holes #1 already documents the `.svg`
dual-membership. After the fix, update the `TEXT_EXTENSIONS` /
`MEDIA_EXTENSIONS` constant tables and the Contract Holes #1 callout to state
the new contract (option 1: "`.svg` is `image` (removed from
`TEXT_EXTENSIONS`); `should_index` returns `False` for `.svg`"; option 2:
"`.svg` is `text` (removed from `MEDIA_EXTENSIONS`); `should_index` returns
`True` for `.svg`"). Remove/adjust the Contract-holes callout for this hole
once merged.

**Reconciliation note (architect, cycle 314, 2026-09-19):** blocker confirmed validator-owned (tests/deep/** test_svg_dual_membership_resolves_to_text pins both .svg memberships + text resolution; both ticket options contradict it) — architect cannot edit tests/deep/**; stays OPEN-PUSHBACK for the IMPL/validator lane.

**Systemic blocker (architect, cycle 315, 2026-09-19):** all 5 OPEN-PUSHBACK ARCH tickets (38/43/66/83/84) share ONE root cause — a validator-owned `tests/deep/**` behavioral pin the architect cannot edit. This ticket's pin: `tests/deep/test_content_type_adversarial.py::TestDetectFromExtension::test_svg_dual_membership_resolves_to_text` (pins the OLD dual membership + text resolution; both ticket options contradict it). Single unblocking action: the validator edits `tests/deep/**` (reconcile the pin to Option 1 — `.svg` removed from `TEXT_EXTENSIONS`, `should_index` False). Ticket stays OPEN-PUSHBACK.
