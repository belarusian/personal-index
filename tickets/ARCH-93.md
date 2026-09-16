# ARCH-93: `validate_sync` "in sync" over-promises — the comparison is one-sided (JSON → HTML only)

Status: CLAIMED 2026-09-16
Component: personal_index/publish_dashboard.py
Issue: #1475

## Symptom

`validate_sync` (line 58) has the docstring (line 59):

    """Validate that HTML embedded metadata and JSON codemap are in sync."""

"In sync" reads as *bidirectional* equality between the two `summary` objects.
The actual comparison (lines 87-89) is **one-sided**:

    87    for key in json_summary:
    88        if json_summary[key] != embedded_summary.get(key):
    89            mismatches.append(f"  {key}: JSON={json_summary[key]} vs HTML={embedded_summary.get(key)}")

The loop iterates only over the keys of the **JSON codemap** `summary` and
checks each against the HTML-embedded `summary` via `.get(key)`. It never
iterates the HTML-embedded `summary`'s keys. So a key that is present **only in
the HTML-embedded summary** (absent from the JSON codemap) is never compared:
`embedded_summary.get(key)` is only ever called for keys that exist in
`json_summary`, and an HTML-only key is simply never visited. `validate_sync`
therefore returns `{"sync": True, "summary": json_summary}` even when the HTML
carries summary keys the JSON codemap does not have. The docstring's "in sync"
claim over-promises; the real contract is the weaker one-sided
"every JSON-summary key matches the HTML-embedded summary; HTML-only keys are
ignored".

## Evidence

The JSON → HTML direction is already pinned (as the *current* behavior) by the
validator's deep test `tests/deep/test_publish_dashboard_adversarial.py`:

    def test_json_key_missing_in_html_detected(self, tmp_path):
        # a key present in the JSON codemap but absent from the HTML-embedded
        # summary is detected as a mismatch -> sync False
        ...

That pins the direction the loop actually checks. The **reverse** direction —
a key present only in the HTML-embedded summary (absent from the JSON codemap)
still yields `sync: True` — is NOT pinned anywhere, and the docstring does not
state that the comparison is one-sided. The current one-sided behavior is the
witness: the existing deep test pins the JSON→HTML half, and the un-pinned
reverse half is exactly what the over-promising docstring hides.

## Why it matters

`validate_sync` is the gate that `main()` uses to decide whether to publish
(and, on a mismatch, whether to prompt "Publish anyway?"). A reader of the
docstring trusts that "in sync" means the two artifacts agree in both
directions. In practice a stale or hand-edited HTML dashboard that carries
extra summary keys (e.g. a leftover `note` field, or a newer generator that
added a key the JSON codemap was not regenerated with) passes the gate
silently and gets published. The disagreement is silent because the docstring
promises more than the code checks.

## Proposed fix (implementer)

Two acceptable resolutions — pick one and make the docstring and behavior
agree:

1. **Document the one-sided contract (minimal, doc-only).** Reword
   `validate_sync`'s docstring (line 59) to state the EXACT contract: it
   checks that every key of the JSON codemap `summary` equals the
   HTML-embedded `summary`'s value for that key (one-sided, JSON → HTML); a
   key present only in the HTML-embedded summary is NOT compared and does not
   affect the result. Do NOT change the code.
2. **Make the comparison bidirectional (code change).** After the existing
   JSON → HTML loop, add a reverse loop over `embedded_summary`'s keys that
   flags any key absent from (or differing in) `json_summary`. This changes
   the reachable behavior (a previously-`sync: True` HTML with extra keys
   becomes `sync: False`) and must keep the existing JSON → HTML mismatches
   intact. This is a larger change and is NOT the minimal fix.

The minimal additive fix is option 1: correct the docstring to the exact
one-sided contract. The JSON → HTML half is already pinned by the deep test;
only the docstring over-promises bidirectionality.

## Acceptance criteria

1. `validate_sync`'s docstring (line 59) states that the comparison is
   one-sided (JSON → HTML): every key of the JSON codemap `summary` must equal
   the HTML-embedded `summary`'s value for that key, and a key present only in
   the HTML-embedded summary is not compared and does not affect the result.
2. No code behavior change: a JSON codemap `summary` of `{"a": 1}` and an
   HTML-embedded `summary` of `{"a": 1, "b": 2}` still yields
   `{"sync": True, "summary": {"a": 1}}` (the HTML-only key `b` is ignored).
3. The existing deep test
   `tests/deep/test_publish_dashboard_adversarial.py::test_json_key_missing_in_html_detected`
   (JSON → HTML direction) still passes unchanged.

## Pinning tests to add (tests/test_publish_dashboard.py)

- `test_validate_sync_html_only_key_still_sync`: write a JSON codemap
  `summary` of `{"total_modules": 1, "total_errors": 0, "total_warnings": 0}`
  and an HTML-embedded `summary` that is the same three keys PLUS an extra key
  (e.g. `"note": "extra"`). Assert `validate_sync(...)["sync"] is True` and
  `["summary"] == {"total_modules": 1, "total_errors": 0, "total_warnings": 0}`
  (the HTML-only key is ignored, not surfaced). One returned object pins both
  the main one-sided behavior and the guard path (extra HTML key does not
  break sync).
- `test_validate_sync_json_only_key_detected` (guard-path pin, mirrors the
  deep test in the unit suite): JSON codemap `summary` with an extra key the
  HTML-embedded `summary` lacks → assert `["sync"] is False` and the mismatch
  names that key. Pins the direction the loop actually checks.

## Docs update (same PR)

`docs/publish_dashboard.md` (new spec page) documents the `validate_sync`
contract and calls out this hole under "Known contract hole";
`docs/README.md` gains the index entry.

## Self-review checklist

- [x] Component named (personal_index/publish_dashboard.py)
- [x] Public contract stated (signature, behavior, error paths, guard inputs)
- [x] file:line evidence (lines 58-59 docstring, 87-89 loop)
- [x] Proposed fix (doc-only minimal + code alternative)
- [x] Acceptance criteria (3)
- [x] Pinning tests to add (2, incl. guard-path input)
- [x] Matching docs/ page update in the SAME PR (docs/publish_dashboard.md + README index)
- [x] Witness check: JSON→HTML direction already pinned by deep test; reverse is the un-pinned half the docstring hides
