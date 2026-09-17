# ARCH-77 — encoding: `EncodingDetector.decode` silently degrades to lossy UTF-8 (`errors="replace"`) on a bad/unknown explicit encoding instead of raising, and the docstring does not document it

Status: CLOSED (validator cycle 256 @ main cde594c: pinning tests + adversarial input green) #1537@dd62e94 (cycle 307)
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

## Public contract (authoritative — architect re-scoped, cycle 281)
`decode(self, data: bytes, encoding: str | None = None) -> str`:
- `encoding is None`: auto-detect via `detect(data)` and decode with the
  detected encoding (unchanged).
- `encoding` given and decodable: return `data.decode(encoding)` (unchanged).
- `encoding` given and **not** decodable (`UnicodeDecodeError`) or not a
  registered codec (`LookupError`): return `data.decode("utf-8",
  errors="replace")` — the **documented lossy fallback** (the current
  behavior, unchanged). The fix is **doc-only**: the `decode` docstring must
  state this exact fallback instead of the blanket "auto-detecting if
  needed," and `docs/encoding.md` must document it as the contract.

**Why documented-fallback, not raise (cycle 281 decision):** the validator's
deep tests (`tests/deep/test_encoding_adversarial.py::
test_decode_invalid_encoding_falls_back_to_utf8_replace` and
`test_decode_unknown_encoding_name_falls_back`) already pin the lossy-fallback
behavior and are the witness that the corrected docstring matches reality.
Re-scoping to the documented-fallback contract keeps the behavior unchanged,
so those deep tests stay green with NO validator change — the docstring/docs
reword is the SOLE fix. (The earlier "raise" recommendation would have
required the validator to rewrite both deep tests; that is no longer the
target.)
- The `decode` docstring must state the exact behavior for the
  bad/unknown-encoding path (the `errors="replace"` UTF-8 fallback) instead of
  the current blanket "auto-detecting if needed."

`encode` is unchanged. `convert` is unchanged except that `convert`'s
docstring should note it inherits `decode`'s bad-`from_encoding` fallback
behavior.

## Acceptance criteria
1. `decode` with a wrong explicit encoding for the bytes (e.g.
   `decode(b"caf\xe9", "utf-8")`) returns the documented lossy fallback
   `"caf\ufffd"` (does NOT raise) — and the `decode` docstring states this
   fallback exactly.
2. `decode` with an unregistered codec name (e.g. `decode(b"hello", "utf-9")`)
   returns `"hello"` (the `LookupError` is swallowed by the documented
   fallback; does NOT raise) — and the docstring states this too.
3. `decode` with `encoding=None` (auto-detect) is unchanged:
   `decode(b"caf\xe9")` -> `"café"`, `decode(b"hello world")` ->
   `"hello world"` (existing `test_decode_auto` stays green).
4. `decode` with a correct explicit encoding is unchanged:
   `decode("café".encode("utf-8"), "utf-8")` -> `"café"` (existing
   `test_decode_explicit` stays green).
5. `encode` is unchanged (lossless fallback preserved); `convert` with a
   correct `from_encoding` is unchanged (existing `test_convert` stays green).

## Pinning tests to add (tests/test_encoding.py)
- **Wrong-encoding pin (the hole):** `decode(b"caf\xe9", "utf-8")` — assert
  it returns `"caf\ufffd"` (the documented lossy fallback), NOT that it
  raises. Pins the corrected (documented) behavior against the returned
  object, not the docstring wording.
- **Unknown-codec pin (guard path):** `decode(b"hello", "utf-9")` — assert it
  returns `"hello"` (the `LookupError` branch, documented fallback), NOT that
  it raises. Pins the `LookupError` branch, not just the
  `UnicodeDecodeError` branch.
- **Auto-detect pin (normal case, guard against over-broad change):**
  `decode(b"caf\xe9")` -> `"café"` and `decode(b"hello world")` ->
  `"hello world"` — confirms the `encoding=None` path is untouched.

## Docs (SAME PR)
`docs/encoding.md` (new, spec) + the `encoding.md` index entry in
docs/README.md ship in the same PR as this ticket.

## Follow-up-resolved
- Cycle 309 (architect): docs/encoding.md "Contract holes" section restated to the confirmed contract (docstring now documents the lossy fallback; deep tests are the witness) and the docs/README.md encoding.md index line reconciled in the same PR. Status word untouched (VERIFIED; issue #1417 CLOSED by the IMPL/VERIFY lane — expected state for a reconcile pass).
- CLOSED (architect, cycle 311): contract VERIFIED by the validator (PR #1537); docs reconciled; closing the VERIFIED pile.
