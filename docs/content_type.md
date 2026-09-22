# content_type — Exact Contract

Module: `personal_index/content_type.py` (331 lines)

## Public API

### `ContentTypeInfo` (dataclass)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| mime_type | str | (required) | Detected MIME type string |
| category | str | (required) | One of `text`, `image`, `video`, `audio`, `media`, `document`, `archive`, `unknown` |
| extension | str | (required) | Extension with leading dot (e.g. `.pdf`); `""` for the unknown fallback |
| is_text | bool | (required) | `category == "text"` |
| is_media | bool | (required) | See the `is_media` divergence note in Contract Holes |
| is_document | bool | (required) | `category == "document"` |
| encoding | str | `"utf-8"` | Always the default; never recomputed |

#### `is_downloadable` (property) -> bool

`return self.is_document or self.is_text`. So `text` and `document` are
downloadable; `image`, `video`, `audio`, `media`, `archive`, `unknown` are not.

### Module constants

| Name | Contents |
|------|----------|
| `CATEGORY_MAP` | dict mapping MIME strings to a category: `text`/`image`/`video`/`audio` map to themselves; `application/json`, `application/xml`, `application/javascript` → `text`; `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument` → `document`; `application/zip`, `application/gzip`, `application/x-tar`, `application/x-rar` → `archive`; `application/octet-stream` → `unknown` |
| `TEXT_EXTENSIONS` | 39 extensions incl. `.txt .md .rst .html .htm .xml .json .yaml .yml .csv .tsv .py .js .ts .java .c .cpp .h .css .sql .sh .bash .zsh .rb .go .rs .php .pl .lua .r .ipynb .toml .ini .cfg .conf .env .log .tex .bib .graphql` |
| `DOCUMENT_EXTENSIONS` | `.pdf .doc .docx .xls .xlsx .ppt .pptx .odt .ods .odp .epub .mobi .djvu` |
| `MEDIA_EXTENSIONS` | image exts (`.jpg .jpeg .png .gif .bmp .webp .svg .ico`) + video (`.mp4 .avi .mkv .mov .wmv .flv .webm`) + audio (`.mp3 .wav .flac .ogg .aac .wma`) |
| `ARCHIVE_EXTENSIONS` | `.zip .tar .gz .bz2 .xz .7z .rar .tgz` |

**Note**: `.svg` is in `MEDIA_EXTENSIONS` only (removed from `TEXT_EXTENSIONS`);
it classifies as `image` and is not indexable (see Contract Holes #1, resolved).

### `ContentTypeDetector`

Stateless except `self._mime_cache: dict[str, ContentTypeInfo]` (an
extension→info cache, keyed `f"ext:{ext}"`, populated only by
`detect_from_extension`).

#### `detect_from_url(self, url: str) -> ContentTypeInfo`

1. `path = url.split("?")[0].split("#")[0]`; `ext = self._get_extension(path)`.
2. If `ext` is truthy → `return self.detect_from_extension(ext)`.
3. Else `mime_type, _ = mimetypes.guess_type(url)`; if truthy →
   `return self._make_info(mime_type, "")`.
4. Else return the unknown fallback (`application/octet-stream`, `unknown`,
   `""`, all flags False).

**Guard paths**:
- URL with no extension and no guessable MIME (e.g. `"https://example.com/"`)
  → unknown fallback.
- Query string / fragment are stripped before the extension is read
  (`"…/a.pdf?v=1"` → `.pdf`).

#### `detect_from_filename(self, filename: str) -> ContentTypeInfo`

Same three-step shape as `detect_from_url`, but `_get_extension(filename)` is
applied to the raw filename (no query/fragment stripping needed).

#### `detect_from_extension(self, ext: str) -> ContentTypeInfo`

1. Normalize: `ext = ext.lower() if ext.startswith(".") else f".{ext.lower()}"`.
2. Cache: `cache_key = f"ext:{ext}"`; if present, return the cached info.
3. `category, mime_type = self._classify_category_from_ext(ext)`.
4. Build `ContentTypeInfo` with `is_text = category == "text"`,
   `is_media = category in ("image", "video", "audio", "media")`,
   `is_document = category == "document"`.
5. Store in `_mime_cache` and return.

**Guard paths**:
- Extension without a leading dot (`.pdf` vs `pdf`) is normalized to the
  dotted, lowercased form before classification and caching.
- Repeated calls with the same normalized extension hit the cache (no
  re-classification).

#### `detect_from_bytes(self, data: bytes) -> ContentTypeInfo`

1. `if not data: return self._unknown_type()` (empty input → unknown).
2. `result = self._check_magic_numbers(data)`; if not None → return it.
3. `text_result = self._try_detect_text(data)`; if not None → return it.
4. Else return `self._unknown_type()`.

`_check_magic_numbers` matches, in order: `%PDF` → `application/pdf`/`.pdf`;
`\x1f\x8b` → `application/gzip`/`.gz`; `PK\x03\x04` → `application/zip`/`.zip`;
`\x89PNG\r\n\x1a\n` → `image/png`/`.png`; `\xff\xd8` → `image/jpeg`/`.jpg`;
`GIF87a`/`GIF89a` → `image/gif`/`.gif`; `RIFF…WEBP` → `image/webp`/`.webp`;
else None.

`_try_detect_text` decodes `data` as UTF-8 and returns `text/plain`/`.txt` iff
the decoded text contains **no** `\x00`; any `UnicodeDecodeError`/`ValueError`
or a null byte → None.

**Guard paths**:
- Empty `b""` → unknown (step 1).
- Bytes that are neither a known magic number nor null-free UTF-8 (e.g.
  `b"\x00\x01\x02"`) → unknown.

#### `classify(self, content_type: str) -> str`

1. `if not content_type: return "unknown"` (empty/None guard).
2. Direct match: `if content_type in CATEGORY_MAP: return CATEGORY_MAP[content_type]`.
3. Prefix match: iterate `CATEGORY_MAP.items()`; first key `k` with
   `content_type.startswith(k)` → return its category.
4. Major-type fallback: `major = content_type.split("/")[0] if "/" in content_type else ""`;
   `text`/`image`/`video`/`audio` map to themselves.
5. Else `return "unknown"`.

**Guard paths**:
- Empty string / `None` → `unknown`.
- A MIME with no slash (e.g. `"pdf"`) → no direct/prefix match, `major == ""`
  → `unknown`.

#### `should_index(self, url: str, content_type: str | None = None) -> bool`

- If `content_type` is truthy → `category = self.classify(content_type)`.
- Else → `info = self.detect_from_url(url)`; `category = info.category`.
- `return category in ("text", "document")`.

So `text` and `document` are indexed; `image`, `video`, `audio`, `media`,
`archive`, `unknown` are not.

### Private helpers

- `_classify_category_from_ext(ext) -> tuple[str, str]`: checks the four
  extension sets **in order** `TEXT_EXTENSIONS` → `DOCUMENT_EXTENSIONS` →
  `MEDIA_EXTENSIONS` → `ARCHIVE_EXTENSIONS` (first membership wins); within
  `MEDIA_EXTENSIONS`, the image subset `{.jpg .jpeg .png .gif .bmp .webp .svg .ico}`
  → `image`, the rest → `media`; `.zip` → `application/zip`, other archives →
  `application/x-archive`; no membership → `("unknown", "application/octet-stream")`.
- `_make_info(mime_type, ext) -> ContentTypeInfo`: `category = self.classify(mime_type)`;
  builds the info with `is_media = category in ("image", "video", "audio")`
  (note: **no** `"media"` — see Contract Holes #2).
- `_unknown_type() -> ContentTypeInfo`: the shared unknown fallback.
- `_get_extension(path) -> str`: strips query/fragment, returns
  `Path(clean).suffix.lower()` (empty string when there is no suffix).

## Contract Holes

### 1. `.svg` dual-membership — RESOLVED (Option 1, ARCH-66 closed cycle 321)

`.svg` was originally listed in **both** `TEXT_EXTENSIONS` and
`MEDIA_EXTENSIONS`; because `_classify_category_from_ext` checks
`TEXT_EXTENSIONS` first, the `MEDIA_EXTENSIONS` entry was dead and `.svg`
resolved to `text`/indexable. The shipped contract is **Option 1**: `.svg` is a
vector image, so it was **removed from `TEXT_EXTENSIONS`** (kept in
`MEDIA_EXTENSIONS` and the image subset). Confirmed behavior:
- `detect_from_extension(".svg")` → `category == "image"`, `is_media is True`,
  `is_text is False`, `mime_type == "image/svg+xml"`.
- `should_index("https://example.com/logo.svg")` → `False` (an SVG image is not
  indexable text).
Option 2 (keep `.svg` as `text`) was rejected: it contradicts the module's own
image-subset intent and the semantic meaning of SVG. Witness: the validator's
deep pin `tests/deep/test_content_type_adversarial.py::test_svg_dual_membership_resolves_to_text`
(reconciled to Option 1 — hard pin, non-strict xfail removed) + 6 adversarial
pins (svg mime, uppercase `.SVG`, `should_index` false with/without query,
other-image-not-indexable, text-still-indexable).

### 2. `is_media` is computed with two divergent category sets

The `is_media` flag is built in two places with **different** category sets:
- `detect_from_extension` (line 183): `category in ("image", "video", "audio", "media")`.
- `_make_info` (line 329): `category in ("image", "video", "audio")` — **omits `"media"`**.

`_make_info` is the path taken by `detect_from_url`/`detect_from_filename`
(no-extension fallback) and `detect_from_bytes` (magic-number matches). The
`"media"` category is only ever produced by `_classify_category_from_ext`
(extension path), so the `_make_info` omission is currently **latent** — a
`media`-category info never flows through `_make_info`. But the two
construction sites that build the same flag disagree, so any future change that
routes a `media` category through `_make_info` would silently drop `is_media`.

## Pinning Tests (for ARCH-66)

1. **`.svg` → image (not text)**: `ContentTypeDetector().detect_from_extension(".svg")`
   → `category == "image"`, `is_media is True`, `is_text is False`,
   `mime_type == "image/svg+xml"`.
2. **`.svg` is NOT indexable**: `ContentTypeDetector().should_index("https://example.com/logo.svg")`
   → `False`.
3. **Guard path — empty bytes**: `ContentTypeDetector().detect_from_bytes(b"")`
   → `category == "unknown"`, `mime_type == "application/octet-stream"`,
   `extension == ""`, all flags False.
4. **Guard path — empty classify**: `ContentTypeDetector().classify("")` →
   `"unknown"`.
5. **Normal path — extension media**: `detect_from_extension(".mp4")` →
   `category == "media"`, `is_media is True` (pins the line-183 set that
   includes `"media"`).
