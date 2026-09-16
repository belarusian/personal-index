# ARCH-82: include_summary is inverted — default keeps FULL content, True makes the export lossy

Status: IMPLEMENTED #1543@79a587c (cycle 311)
Component: personal_index.export_markdown (personal_index/export_markdown.py)
Issue: #1441

## Symptom

`ExportConfig.include_summary` (line 29, default `False`) is named as if it
*adds* a summary, but the code uses it as a **replace** flag. All three
renderers use the identical expression
`self._truncate(content, 200) if self.config.include_summary else content`:

- line 173 (`_render_md_item`, markdown)
- line 207 (`_export_html`)
- line 243 (`_export_plain_text`)

So with the **default** `include_summary=False` the **full** content is
emitted, and setting `include_summary=True` **replaces** the content with a
lossy 200-char word-boundary truncation + `...`. A caller who reads the flag
name and sets `include_summary=True` expecting a summary *in addition to* the
content instead gets a lossy export that silently discards most of the
content. The semantics are inverted relative to the flag name.

## Evidence

- `personal_index/export_markdown.py:29` — `include_summary: bool = False`.
- `personal_index/export_markdown.py:173` — markdown:
  `lines.append(self._truncate(content, 200) if self.config.include_summary else content)`.
- `personal_index/export_markdown.py:207` — HTML:
  `display = self._truncate(content, 200) if self.config.include_summary else content`.
- `personal_index/export_markdown.py:243` — plain text:
  `display = self._truncate(content, 200) if self.config.include_summary else content`.
- `tests/deep/test_export_markdown_adversarial.py:424` —
  `test_truncate_summary_mode_applies_to_content` only asserts `"..." in out`
  for the `True` case. It does **not** pin that the full content is dropped
  when `True`, nor that the default (`False`) keeps the full content. The
  inversion is therefore unpinned.

## Failing input / observed vs expected

- Input: one item with `content = "word " * 50` (250 chars, > 200).
- Observed (default `include_summary=False`): the full 250-char content is
  emitted verbatim (no truncation, no `...`).
- Observed (`include_summary=True`): the content is replaced by a 200-char
  word-boundary truncation + `...`; the tail of the original content is
  dropped.
- Expected (per the flag name `include_summary`): `False` should mean "no
  summary" (content omitted or full, consistently) and `True` should mean
  "include a summary" — i.e. the flag should *add* a summary, not *replace*
  the content with a lossy truncation. The current default (full content) and
  the `True` behavior (lossy replacement) are inverted relative to the name.

## Contract (what the fix must do)

Pick ONE of the two coherent semantics and make the code + docs + tests agree:

Option A (rename to match behavior — recommended, smallest change):
1. Rename the flag to `truncate_content: bool = False` (or
   `summary_only`), so the name states that `True` *replaces* the content with
   a 200-char truncation.
2. Keep the three renderer expressions as-is (they already match the renamed
   flag).
3. Update `docs/export_markdown.md` to state the exact conditional.

Option B (make the flag additive):
1. `include_summary=False` → emit the full content (unchanged).
2. `include_summary=True` → emit the full content **plus** a 200-char
   `**Summary:** ...` line (additive, not a replacement).
3. Update the three renderer expressions and `docs/export_markdown.md`.

Whichever option is chosen, the three renderers (markdown/HTML/plain text)
must stay consistent with each other and with the docs.

## Acceptance Criteria

- [ ] The flag name and its behavior agree: a reader of the flag name can
      predict whether the content is kept full, truncated, or summarized.
- [ ] All three renderers (markdown, HTML, plain text) apply the same
      content policy for the same config.
- [ ] The default config produces the same content policy as before the fix
      (no silent behavior change for existing callers relying on the default).
- [ ] `docs/export_markdown.md` "Documented Contract Hole" section is updated
      to reflect the corrected (non-inverted) contract.
- [ ] The existing deep test
      `test_truncate_summary_mode_applies_to_content` still passes (or is
      updated to pin the corrected semantics).

## Pinning Tests to Add

In `tests/test_export_markdown.py` (or the deep adversarial file):

- `test_default_config_keeps_full_content`: with the default `ExportConfig()`
  and an item whose `content` is > 200 chars, assert the **full** content
  string is present in the markdown output (pins the default = full-content
  behavior).
- `test_summary_flag_replaces_content_with_truncation` (Option A) or
  `test_summary_flag_adds_summary_line` (Option B): with
  `ExportConfig(include_summary=True)` (or the renamed flag) and a > 200-char
  content, assert the exact corrected policy — either the full content is
  dropped and only the `...`-terminated truncation remains (Option A), or the
  full content is present **and** a separate `**Summary:**` line with the
  truncation is present (Option B).
- The same two assertions repeated for `ExportFormat.HTML` and
  `ExportFormat.PLAIN_TEXT` so all three renderers are pinned to the same
  policy.

## Docs update (same PR)

`docs/export_markdown.md` "Documented Contract Hole" section: replace the
inverted-flag description with the corrected contract (whichever option is
chosen), and move the behavior into the `ExportConfig` field description under
Public API.

## Design decision (architect, cycle 286)

**Chosen option: A (rename the flag to match behavior).**

The flag is renamed `include_summary` -> `truncate_content: bool = False`.
The name now states the behavior exactly: `True` *replaces* the content with
a 200-char word-boundary truncation + `...` (lossy); `False` (the default)
emits the full content verbatim.

Exact contract (all three renderers, identical policy for the same config):
- markdown `_render_md_item` (line 173)
- HTML `_export_html` (line 207)
- plain text `_export_plain_text` (line 243)

each use `self._truncate(content, 200) if self.config.truncate_content else
content`.

Why Option A over Option B: it is the smallest change — the three renderer
expressions already match the renamed flag, so only the flag name changes and
the default content policy is preserved (no silent behavior change for
existing callers relying on the default). Option B (additive `**Summary:**`
line) would require editing all three renderer expressions and changes the
`True` output shape.

Implementer actions (this ticket stays OPEN until they land):
1. Rename the code flag `include_summary` -> `truncate_content` in
   `ExportConfig` (line 29) and the three renderer expressions (lines 173,
   207, 243). The expressions are unchanged in form — only the attribute name.
2. Add the pinning tests named above (default keeps full content; `True`
   drops the full content leaving only the `...`-terminated truncation;
   repeated for all three formats).
3. `docs/export_markdown.md` was updated in the SAME PR (cycle 286) to state
   the confirmed contract; the docs "Documented Contract Hole" section is now
   "Confirmed Contract (ARCH-82, Option A)".

Status remains OPEN (the implementer claims and implements; the architect
closes after verification).
