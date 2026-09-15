# ARCH-100: cli_top.py is a dead parallel `top` implementation whose JSON contract has diverged from the live command

- **Status:** OPEN
- **Component:** `personal_index/cli_top.py`
- **Kind:** contract hole (dead module + divergent JSON contract)
- **Issue:** #1496

## Symptom

`personal_index/cli_top.py` defines `top_pages`, a click command named
`"top"` (line 19), but it is **never imported or registered** anywhere in
`personal_index/` — `grep -rn 'cli_top' personal_index/ --include=*.py`
returns no import (the only hit is the module's own file). The LIVE `top`
command is the inline `def top` at `personal_index/cli.py:906` (registered on
the `main` group via `@main.command()` at `cli.py:901`). So `top_pages` is
unreachable from the `personal-index` CLI; `personal-index top` runs the
`cli.py` command, not this module.

Worse, the two implementations have **diverged on the JSON contract** for the
same `top` command name:

- **Live** (`cli.py:919`): `json.dumps({"top_pages": [p.to_dict() for p in
  pages]}, indent=2, default=str)` — each entry is the full `IndexedPage`
  `to_dict()` (url, title, content, keywords, matched_interests, domain,
  status_code, content_length, language, score, indexed_at, source_interest,
  word_count). NO `rank`, NO top-level `total`, NO `tags`.
- **Dead** (`cli_top.py:39-45`): `{"top_pages": [{"rank": i+1, "url", "title",
  "score", "crawled_at", "tags": []} ...], "total": len(pages)}` — a
  hand-built 6-key entry (NOT `to_dict()`), plus a top-level `total`, where
  `tags` is a **hardcoded always-empty list** even though `IndexedPage`
  (`personal_index/models.py:282`) has **no `tags` field** (its per-page data
  is `keywords` and `matched_interests`, both silently dropped here).

The two contracts are pinned by different tests, so both are "green" while
describing the same command differently:
- `tests/test_cli_top.py` pins the DEAD contract (`assert "total" in data`,
  `page["rank"] == 1`).
- `tests/deep/test_cli_top_adversarial.py` pins the LIVE contract
  (`assert set(data.keys()) == {"top_pages"}`, entries are `to_dict()`).

This is a dead-module + contract-drift hole (the same class as ARCH-98's
`cli_export.py` `export_cmd`): a parallel implementation that is unreachable
from the CLI and whose output contract no longer matches the live command.

## Evidence (file:line)

- `personal_index/cli_top.py:19` — `def top_pages(ctx, limit, fmt, data_dir)`
  under `@click.command("top")` (line 17).
- `personal_index/cli_top.py:39-45` — `_to_json` returns
  `{"top_pages": [{rank, url, title, score, crawled_at, tags: []}], "total":
  len(pages)}`.
- `personal_index/cli_top.py:42` — `"tags": []` hardcoded; `IndexedPage`
  (`models.py:282-299`) has no `tags` field (fields: url, title, content,
  keywords, matched_interests, crawled_at, domain, status_code,
  content_length, language, score, indexed_at, source_interest, word_count).
- `grep -rn 'cli_top' personal_index/ --include=*.py` → no import (module is
  never wired into the CLI).
- `personal_index/cli.py:901` — `@main.command()`; `cli.py:906` — `def top`
  (the LIVE command).
- `personal_index/cli.py:919` — live JSON: `{"top_pages": [p.to_dict() for p
  in pages]}` (no `rank`/`total`/`tags`).
- `personal_index/index.py:154-156` — `list_pages()` returns pages sorted by
  `score` descending (both commands rely on this for "highest-scored").
- **Witness (validator-owned, pins the LIVE contract):**
  `tests/deep/test_cli_top_adversarial.py:153-165`
  (`test_json_is_valid_and_shaped`) asserts `set(data.keys()) == {"top_pages"}`
  and that each entry has `url`/`title`/`score` — the live `to_dict()` shape,
  NOT the dead `rank`/`total`/`tags` shape. This is the witness that the live
  contract (the one users actually get) is `to_dict()`-only.
- **Dead-contract pin (implementer-owned):** `tests/test_cli_top.py:97-100`
  asserts `"total" in data` and `page["rank"] == 1` — pins the dead module's
  divergent contract.

## Public contract (what the fix must preserve / establish)

The LIVE `personal-index top` command (`cli.py:906`) must keep its current
behavior unchanged: text output (`Top N pages by score:`, numbered entries,
score to 4 decimals) and JSON output `{"top_pages": [p.to_dict() ...]}`. The
fix is a DECISION about the dead `cli_top.py` module; either option is
acceptable, but `docs/cli_top.md` and this ticket must state which was chosen:

- **Option A (delete the dead module — preferred, minimal):** remove
  `personal_index/cli_top.py` and its now-orphaned unit test
  `tests/test_cli_top.py` (which pins only the dead contract). The live
  `cli.py` command and its deep test are untouched. This eliminates the
  divergent contract and the phantom `tags: []` field. No change to the live
  CLI surface.
- **Option B (wire it up and reconcile the contract):** register `top_pages`
  on the `main` group AND make its JSON contract match the live command
  (emit `p.to_dict()`, drop the phantom `tags: []` and the divergent
  `rank`/`total`), then reconcile `tests/test_cli_top.py` to the live shape.
  This is the larger diff and only worth it if `cli_top.py` is intended to be
  the canonical home for the `top` command (in which case the inline `cli.py`
  `top` should be removed instead, to avoid two live `top` registrations).

Guard inputs the contract must pin (whichever option):
- Empty index (no file / explicit empty file) → `No indexed pages found. Run
  'personal-index pipeline' first.` (deep test `test_empty_index_no_file`,
  `test_empty_index_explicit_empty_file`).
- Negative limit → clamped to 0 → same empty hint (deep test
  `test_negative_limit_clamped_to_zero`, `test_large_negative_limit_clamped_to_zero`).
- Zero limit → no pages (deep test `test_zero_limit_no_pages`).
- Limit larger than pool → all pages shown (deep test
  `test_limit_larger_than_pool_shows_all`).
- (Option B only) JSON entry shape must equal `p.to_dict()` (no `rank`, no
  `total`, no `tags`), matching the live command.

## Acceptance criteria

1. The `top` command reachable from the CLI has exactly ONE implementation and
   ONE JSON contract. No dead parallel implementation with a divergent
   contract remains.
2. `docs/cli_top.md` states which option (A or B) was implemented and the
   resulting reachable input surface; the "Known contract hole" section is
   updated to reflect the resolution.
3. The phantom `tags: []` field is gone from the reachable `top` JSON output
   (Option A: module deleted; Option B: `_to_json` emits `to_dict()`).
4. The validator deep test `tests/deep/test_cli_top_adversarial.py` stays
   green (it pins the live contract, which is unchanged by either option).
5. `grep -rn 'cli_top' personal_index/ --include=*.py` is consistent with the
   chosen option: Option A → no hits (module deleted); Option B → a
   registration import on the `main` group.

## Pinning tests to add (IMPLEMENTER owns tests/**)

- **Option A (preferred, minimal):** delete `tests/test_cli_top.py` (it pins
  only the dead contract). The witness that the live contract is intact is the
  existing `tests/deep/test_cli_top_adversarial.py` (validator-owned) — the
  implementer re-runs it after deletion and confirms green. No new test.
- **Option B:** reconcile `tests/test_cli_top.py` to the live `to_dict()`
  shape (drop the `total`/`rank`/`tags` assertions, assert `to_dict()` keys)
  and add a `CliRunner` test driving `["top", "--format", "json"]` against
  `cli.main` that pins the reconciled entry shape plus the empty-index /
  negative-limit guard paths.

## Proposed fix

Option A is preferred: `cli_top.py` is unreachable dead code, and the live
`cli.py` `top` command (with its full `to_dict()` JSON and the validator deep
test suite) is the real, tested, user-facing implementation. Deleting the dead
module and its orphaned unit test removes the divergent contract and the
phantom `tags: []` field with the smallest possible diff. Option B is the
larger diff (reconcile two JSON contracts + rewire registration) and is only
worth it if the team intends `cli_top.py` to be the canonical `top` home.

## Self-review checklist (architect)

- [x] Component named (`personal_index/cli_top.py`).
- [x] Public contract stated (live command surface, guard inputs, the two
      resolution options, the divergent JSON contract).
- [x] Evidence is file:line, verified against current code on this branch.
- [x] Witness identified (validator deep test pins the LIVE `to_dict()`
      contract; unit test pins the dead contract).
- [x] Acceptance criteria are checkable without conversation.
- [x] Pinning tests specified (Option A: delete orphaned unit test, deep test
      is the witness; Option B: reconcile unit test + new end-to-end test).
- [x] Docs page `docs/cli_top.md` shipped in the SAME PR and states the hole
      + the option to choose.
- [x] No code/test written by architect (design-only; implementer owns the
      fix + tests).
