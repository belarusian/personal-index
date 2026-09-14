# IMPL-11: ARCH-66 infeasible — validator-owned deep test pins the OLD `.svg` classification; both ticket options contradict it

Status: OPEN
Component: `personal_index/content_type.py`
Refs: ARCH-66 (#1380)

## Blocking sentence (quoted from ARCH-66)

> `.svg` must classify as **`image`**, matching its presence in the
> `MEDIA_EXTENSIONS` image subset (line 153). The `TEXT_EXTENSIONS` entry for
> `.svg` is the anomaly (a copy-paste artifact) and must be removed so the
> `MEDIA_EXTENSIONS` branch is reachable.

## Why this is infeasible for the implementer

ARCH-66 offers exactly two options, and the validator-owned deep test
`tests/deep/test_content_type_adversarial.py::TestDetectFromExtension::test_svg_dual_membership_resolves_to_text`
pins the OLD behavior in a way that BOTH options contradict:

    def test_svg_dual_membership_resolves_to_text(self, det):
        # .svg appears in BOTH TEXT_EXTENSIONS and MEDIA_EXTENSIONS; the
        # classifier checks TEXT_EXTENSIONS first, so it resolves to "text".
        assert ".svg" in TEXT_EXTENSIONS
        assert ".svg" in MEDIA_EXTENSIONS
        info = det.detect_from_extension(".svg")
        assert info.category == "text"
        assert info.is_text is True
        assert info.is_media is False

- **Option 1** (remove `.svg` from `TEXT_EXTENSIONS`, keep in `MEDIA_EXTENSIONS`):
  the first assertion `assert ".svg" in TEXT_EXTENSIONS` FAILS. The ticket's
  acceptance criteria 1-2 (`.svg` → `image`, `should_index` → `False`) also
  contradict the deep test's `category == "text"` / `is_media is False` pins.
- **Option 2** (remove `.svg` from `MEDIA_EXTENSIONS`, keep in `TEXT_EXTENSIONS`):
  the second assertion `assert ".svg" in MEDIA_EXTENSIONS` FAILS.

The deep test asserts the DUAL membership itself (`.svg` in BOTH sets) AND the
`text` resolution. Satisfying either ticket option requires removing `.svg`
from one of the two sets, which the deep test explicitly forbids. CI runs
`pytest tests/` which includes `tests/deep/`, so either option lands a RED
suite and the PR cannot be merged.

The implementer is HARD LIMITED to `personal_index/**` and `tests/**` (NEVER
`tests/deep/**`). I cannot modify the validator's deep test to align it with
either corrected contract.

## Required resolution

The validator (personal-index-5) must update
`tests/deep/test_content_type_adversarial.py::TestDetectFromExtension::test_svg_dual_membership_resolves_to_text`
to match the chosen option:
- Option 1: assert `".svg" not in TEXT_EXTENSIONS`, `".svg" in MEDIA_EXTENSIONS`,
  `info.category == "image"`, `info.is_media is True`, `info.is_text is False`,
  `info.mime_type == "image/svg+xml"`.
- Option 2: assert `".svg" in TEXT_EXTENSIONS`, `".svg" not in MEDIA_EXTENSIONS`,
  `info.category == "text"`, `info.is_text is True`, `info.is_media is False`.

Once that deep test is updated, the implementer can land the matching
`content_type.py` change on CI green and stamp ARCH-66 IMPLEMENTED.

Alternatively, the architect may clarify in docs/content_type.md which option
is authoritative (the ticket prefers Option 1) so the validator's deep test and
the ticket's acceptance criteria agree on a single contract.
