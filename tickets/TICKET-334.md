# TICKET-334 — content_type.ContentTypeInfo.category comment omits the "media" value the detector actually produces

- Status: OPEN
- Class: (b) doc/behavior drift
- Module: personal_index/content_type.py
- Issue: #506

## Symptom
The `ContentTypeInfo.category` field comment (line 15) documents a closed
set of values: `"text", "image", "video", "audio", "document", "archive",
"unknown"`. But `ContentTypeDetector._classify_category_from_ext` (line 155)
actually returns the value `"media"` for non-image media extensions (e.g.
`.mp4`, `.mp3`, `.avi`, `.mkv`, `.flac`). So the documented set is
incomplete: it under-promises the real value space. A reader trusting the
comment would not expect `info.category == "media"` to be possible, yet
`detect_from_extension(".mp4")` produces exactly that.

## Evidence
- `sed -n '13,16p' personal_index/content_type.py` shows the field comment
  `category: str  # "text", "image", "video", "audio", "document",
  "archive", "unknown"` — no "media".
- `sed -n '151,156p' personal_index/content_type.py` shows
  `_classify_category_from_ext` returning `return "media", mime_type or
  "application/octet-stream"` (line 155) for media extensions that are not
  in the image subset.
- `sed -n '183p' personal_index/content_type.py` confirms the code itself
  treats "media" as a real category: `is_media=category in ("image",
  "video", "audio", "media")`.
- `grep -rn '"media"' personal_index/ tests/` shows the "media" category
  value is internal-only (no external consumer depends on it), so the
  correct minimal fix is to document the value the code already produces,
  not to change behavior.

## Minimal additive fix
Add `"media"` to the documented value set in the `category` field comment
(line 15). Change
`category: str  # "text", "image", "video", "audio", "document", "archive", "unknown"`
to
`category: str  # "text", "image", "video", "audio", "media", "document", "archive", "unknown"`.

Add ONE regression test
`TestContentTypeInfo::test_media_category_is_documented` that asserts the
`ContentTypeInfo.category` field comment contains the string `"media"`, so
the documented set cannot silently drift from the value the detector
actually emits again.
