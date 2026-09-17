# Encoding (`personal_index.encoding`)

Status: **spec** — audited against current code (cycle 245).

`EncodingDetector` (stateless; no constructor args) detects, decodes, encodes
and converts text encodings, plus three whitespace/control-char text helpers.
It is a pure utility: no persistence, no I/O, no side effects.

## EncodingResult
Dataclass. Fields: `encoding: str`, `confidence: float`,
`language: str | None = None`. `language` is **always** left at its default
(`None`) — `detect` performs no language detection.

## detect(data: bytes) -> EncodingResult
Fixed priority cascade; returns the first match. Order matters:

1. UTF-8 BOM (`\xef\xbb\xbf`) -> `encoding="utf-8"`, `confidence=1.0`.
2. UTF-16 BOM (`\xff\xfe` LE or `\xfe\xff` BE) -> `encoding="utf-16"`,
   `confidence=1.0`.
3. Pure ASCII (every byte < 0x80) -> `encoding="ascii"`, `confidence=0.9`.
   **Takes priority over valid UTF-8**, so any ASCII-only payload — including
   the empty `b""` — is reported `ascii`, never `utf-8`.
4. Valid UTF-8 (decodes cleanly but is not pure ASCII) -> `encoding="utf-8"`,
   `confidence=0.8`.
5. Fallback (not valid UTF-8) -> `encoding="iso-8859-1"`, `confidence=0.5`.

`language` is always `None`.

## decode(data: bytes, encoding: str | None = None) -> str
- `encoding is None`: auto-detect via `detect(data)` and decode with the
  detected encoding.
- `encoding` given: decode with that encoding.
- **On `UnicodeDecodeError` or `LookupError` (unknown codec name), silently
  falls back to `data.decode("utf-8", errors="replace")`.** This is the
  confirmed contract (ARCH-77, resolved) — see below.

## encode(text: str, encoding: str = "utf-8") -> bytes
Encode with `encoding`; on `UnicodeEncodeError` or `LookupError` fall back to
`text.encode("utf-8")` (lossless for any `str`, since `str` is always
UTF-8-encodable).

## convert(data: bytes, from_encoding: str, to_encoding: str = "utf-8") -> bytes
`decode(data, from_encoding)` then `encode(text, to_encoding)`. Inherits the
`decode` fallback behavior (see Confirmed contract below).

## Text helpers
- `normalize_whitespace(text) -> str` — `re.sub(r"\s+", " ", text).strip()`.
- `remove_control_chars(text) -> str` — strips `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]`
  (keeps `\t` `\n` `\r`).
- `sanitize(text) -> str` — `remove_control_chars` then `normalize_whitespace`.

## Confirmed contract (ARCH-77, resolved)
- **`decode`'s lossy UTF-8 fallback on a bad/unknown explicit encoding is the
  confirmed contract (ARCH-77).** When the caller passes an explicit
  `encoding` that cannot decode the data (`UnicodeDecodeError`) or is not a
  registered codec (`LookupError`), `decode` does **not** raise — it returns
  `data.decode("utf-8", errors="replace")`, substituting U+FFFD replacement
  characters for undecodable bytes. This is now stated in the `decode`
  docstring ("the error is NOT raised: the method falls back to
  `data.decode("utf-8", errors="replace")` ... a documented lossy fallback").
  Observed: `decode(b"caf\xe9", "utf-8")` -> `"caf\ufffd"` (lossy),
  whereas the correct lossless result for the same bytes is `"café"` (what
  `decode(b"caf\xe9")` auto-detects, since `detect` reports `iso-8859-1`).
  The `encode` fallback is lossless by construction: `str` is always
  UTF-8-encodable. The `convert` path inherits the `decode` fallback only
  when `from_encoding` is wrong.
- **Witness:** the pinning deep tests
  `tests/deep/test_encoding_adversarial.py::test_decode_invalid_encoding_falls_back_to_utf8_replace`
  (the `UnicodeDecodeError` branch returns U+FFFD, does not raise) and
  `::test_decode_unknown_encoding_name_falls_back` (the `LookupError` branch
  returns the clean UTF-8 decode) pin the confirmed behavior against the
  returned object; the corrected docs match reality (no code/test change
  required).
- **Adjacent behaviors that are NOT holes** (do not re-ticket): the `detect`
  cascade (all five rules, the ASCII-over-UTF-8 priority, empty-bytes->ascii,
  `language` always `None`) is fully pinned by `TestDetectContract` and is
  correct; `encode`'s fallback is lossless by construction; the three text
  helpers are pure and correct.
