# ARCH-77 — encoding: `EncodingDetector.decode` silently degrades to lossy UTF-8 (`errors="replace"`) on a bad/unknown explicit encoding instead of raising, and the docstring does not document it

Status: OPEN-PUSHBACK (IMPL-12, cycle 304)
Component: `personal_index/encoding.py` — `EncodingDetector.decode` (lines 66-74); the fallback `return data.decode("utf-8", errors="replace")` (line 74); the `decode` docstring (line 67). `convert` (lines 83-85) inherits the hole via its `decode` call.
Umbrella: ARCH-2 (#983)
Issue: #1417
Docs: `docs/encoding.md` (Contract holes, ARCH-77)

## Problem
`decode`'s docstring (line 67) reads only "Decode bytes to string,
auto-detecting if needed." — it says nothing about what happens when the
caller passes an **explicit** `encoding` that cannot decode the data.

The body (lines 66-74):

    def decode(self, data: bytes, encoding: str | None = None) -> str:
        if encoding is None:
            result = self.detect(data)
            encoding = result.encoding
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return data.decode("utf-8", errors="replace")

When `encoding` is given and `data.decode(encoding)` raises
`UnicodeDecodeError` (wrong codec for the bytes) or `LookupError` (the codec
name is not registered, e.g. `"utf-9"`), `decode` does **not** propagate the
error — it silently returns `data.decode("utf-8", errors="replace")`,
substituting U+FFFD replacement characters for every undecodable byte. The
caller receives corrupted text with no signal that the requested encoding was
wrong.

This is surprising/lossy where a caller would reasonably expect either a
correct decode or an exception. Verified (cycle 245):

    d = EncodingDetector()
    data = "café".encode("iso-8859-1")          # b"caf\xe9"
    d.decode(data, "utf-8")                      # -> "caf\ufffd"  (LOSSY, no error)
    d.decode(data)                               # -> "café"         (lossless; detect -> iso-8859-1)
    d.decode(b"hello", "utf-9")                  # -> "hello"        (LookupError swallowed, no error)

The same bytes decode losslessly when auto-detected (`detect` reports
`iso-8859-1`), so the loss is purely the consequence of a wrong explicit
encoding being silently papered over.

## What is NOT a hole (do not re-ticket)
- The `detect` cascade (all five rules, ASCII-over-UTF-8 priority,
  empty-bytes->ascii, `language` always `None`) is correct and fully pinned by
  `TestDetectContract` in `tests/test_encoding.py`.
- `encode`'s fallback (`except (UnicodeEncodeError, LookupError): return
  text.encode("utf-8")`, lines 76-81) is **lossless by construction** — a
  `str` is always UTF-8-encodable — so it is not a hole.
- The three text helpers (`normalize_whitespace`, `remove_control_chars`,
  `sanitize`) are pure and correct.
- `convert` inherits the hole **only** when `from_encoding` is wrong; a
  correct `from_encoding` is unaffected.

## Public contract (recommended)
`decode(self, data: bytes, encoding: str | None = None) -> str`:
- `encoding is None`: auto-detect via `detect(data)` and decode with the
  detected encoding (unchanged).
- `encoding` given and decodable: return `data.decode(encoding)` (unchanged).
- `encoding` given and **not** decodable (`UnicodeDecodeError`) or not a
  registered codec (`LookupError`): **raise** the original exception rather
  than silently returning a lossy `errors="replace"` string. The caller who
  named a specific encoding gets a clear failure, not corrupted text.
  (Alternative acceptable contract: keep the fallback but make it explicit and
  documented — log a warning and/or return a sentinel — but the default
  recommendation is to raise, matching the "a wrong explicit encoding is a
  caller error" expectation. The implementer picks ONE and the docstring must
  state it exactly.)
- The `decode` docstring must state the exact behavior for the
  bad/unknown-encoding path (raise, or the documented fallback) instead of the
  current blanket "auto-detecting if needed."

`encode` and `convert` are unchanged except that `convert`'s docstring should
note it inherits `decode`'s bad-`from_encoding` behavior.

## Acceptance criteria
1. `decode` with a wrong explicit encoding for the bytes (e.g.
   `decode(b"caf\xe9", "utf-8")`) raises `UnicodeDecodeError` (or, if the
   documented-fallback contract is chosen, returns a value that is NOT
   silently equal to a lossy `errors="replace"` string without a documented
   signal) — it does not return `"caf\ufffd"` silently.
2. `decode` with an unregistered codec name (e.g. `decode(b"hello", "utf-9")`)
   raises `LookupError` (or the documented fallback) — it does not silently
   return `"hello"` with no signal.
3. `decode` with `encoding=None` (auto-detect) is unchanged:
   `decode(b"caf\xe9")` -> `"café"`, `decode(b"hello world")` ->
   `"hello world"` (existing `test_decode_auto` stays green).
4. `decode` with a correct explicit encoding is unchanged:
   `decode("café".encode("utf-8"), "utf-8")` -> `"café"` (existing
   `test_decode_explicit` stays green).
5. `encode` is unchanged (lossless fallback preserved); `convert` with a
   correct `from_encoding` is unchanged (existing `test_convert` stays green).

## Pinning tests to add (tests/test_encoding.py)
- **Wrong-encoding pin (the hole):** `decode(b"caf\xe9", "utf-8")` — assert it
  raises `UnicodeDecodeError` (or the documented-fallback contract's observable
  signal), NOT that it returns `"caf\ufffd"` silently. Pins the corrected
  behavior against the returned/raised object, not the docstring.
- **Unknown-codec pin (guard path):** `decode(b"hello", "utf-9")` — assert it
  raises `LookupError` (or the documented fallback), NOT that it silently
  returns `"hello"`. Pins the `LookupError` branch, not just the
  `UnicodeDecodeError` branch.
- **Auto-detect pin (normal case, guard against over-broad change):**
  `decode(b"caf\xe9")` -> `"café"` and `decode(b"hello world")` ->
  `"hello world"` — confirms the `encoding=None` path is untouched.

## Docs (SAME PR)
`docs/encoding.md` (new, spec) + the `encoding.md` index entry in
docs/README.md ship in the same PR as this ticket.
