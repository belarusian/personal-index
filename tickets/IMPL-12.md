# IMPL-12 — ARCH-77: raise contract conflicts with validator-owned deep tests pinning the lossy fallback

Status: CLOSED (architect resolved, cycle 281: re-scoped ARCH-77 to the documented-fallback contract — the validator deep tests already pin this behavior, so no tests/deep/** change is needed; the docstring/docs reword is the sole fix and ARCH-77 is back to OPEN for the implementer)
Author: FEATURE-IMPLEMENTER (ARCH lane), cycle 304
Blocks: tickets/ARCH-77.md (Issue #1417)

## Blocking sentence (quoted from ARCH-77)
From ARCH-77 "Public contract (recommended)":

    encoding given and not decodable (UnicodeDecodeError) or not a registered
    codec (LookupError): raise the original exception rather than silently
    returning a lossy errors="replace" string.

And from ARCH-77 "Acceptance criteria":

    1. decode with a wrong explicit encoding for the bytes (e.g.
       decode(b"caf\xe9", "utf-8")) raises UnicodeDecodeError ... it does not
       return "caf\ufffd" silently.
    2. decode with an unregistered codec name (e.g. decode(b"hello", "utf-9"))
       raises LookupError ... it does not silently return "hello" with no signal.

## Why this is infeasible in the ARCH lane
The recommended raise contract is directly contradicted by two validator-owned
deep tests in tests/deep/test_encoding_adversarial.py that pin the CURRENT
lossy-fallback behavior:

- test_decode_invalid_encoding_falls_back_to_utf8_replace (line 130):
  asserts DET.decode(b"\x80\x81", "utf-8") returns a str containing "\ufffd"
  and does NOT raise.
- test_decode_unknown_encoding_name_falls_back (line 139):
  asserts DET.decode(b"hello", "not-a-real-encoding") == "hello" (LookupError
  swallowed, does NOT raise).

Implementing the raise contract makes both deep tests fail (verified: running
the full gate after the raise change produced
"FAILED tests/deep/test_encoding_adversarial.py::test_decode_invalid_encoding_falls_back_to_utf8_replace").

tests/deep/** is the VALIDATOR's path (HARD LIMITS: never write to it). The
ARCH lane cannot edit those tests, so the raise contract cannot be merged with
CI green. The ticket's alternative contract (keep the fallback but make it
explicit/documented with a signal) is not what the acceptance criteria and the
three named pinning tests assert (they assert pytest.raises), so it is not a
drop-in either.

## What the implementer did
- Claimed ARCH-77 (branch impl304/encoding-decode-bad-encoding-raise, claim
  commit 80ecfca).
- Implemented the raise contract + 3 pinning tests + docstring reword; the
  local gate failed only on the two validator-owned deep tests above.
- Reverted the implementation to keep the tree at the claim state.
- Set ARCH-77 to OPEN-PUSHBACK.

## Requested resolution (architect)
Either (a) the architect re-scopes ARCH-77 to the documented-fallback contract
and rewrites the acceptance criteria + pinning tests to match (and the
validator updates the two deep tests to pin the documented signal), or
(b) the validator updates the two deep tests to the raise contract and the
architect confirms the raise contract is the target, after which the ARCH lane
can re-claim and implement.
