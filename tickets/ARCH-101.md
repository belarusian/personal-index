# ARCH-101: `health` CLI exposes 5 of the 7 checker knobs — `max_title_length` and `min_tags` are unreachable from the CLI

- **Status:** VERIFIED (validator cycle 271 @ main 76e12b6; both knobs wired: --max-title-length + --min-tags in cli_health.py:19-20, _build_config passes both at :67-69; pinning tests tests/test_cli_health.py 8 passed; adversarial: max_title_length=0 -> 0, min_tags=5 -> 5; [was IMPLEMENTED #1573@716bbabaa8bbd0994a9a62ebd9962e40d2cf2f05 impl329 cycle 329])
- **Component:** `personal_index/cli_health.py` (drives `personal_index.content_health.ContentHealthCheck`)
- **Kind:** contract hole (unexposed config knobs — two of seven checks untunable from the CLI)
- **Issue:** #1499

## Symptom

`personal_index/content_health.py:194-202` defines `ContentHealthCheck` with
**seven** fields:

    min_content_length: int = 50
    min_title_length:   int = 3
    max_title_length:   int = 200
    require_tags:       bool = False
    min_tags:           int = 1
    require_score:      bool = False
    min_score:          float = 0.0

But the LIVE `health` command (`personal_index/cli_health.py:14-18`) exposes
only **five** options:

    --data-dir
    --min-content-length   (int, default 50)
    --min-title-length     (int, default 3)
    --require-tags         (is_flag)
    --min-score            (float, default 0.0)

and `_build_config` (`cli_health.py:61-68`) constructs the config with only
five of the seven fields:

    def _build_config(min_content_length, min_title_length, require_tags, min_score):
        return ContentHealthCheck(
            min_content_length=min_content_length,
            min_title_length=min_title_length,
            require_tags=require_tags,
            require_score=min_score > 0,
            min_score=min_score,
        )

So `max_title_length` (default **200**, gates the `title_too_long` check at
`content_health.py:308-321`) and `min_tags` (default **1**, gates the
`missing_tags` check at `content_health.py:338-354`) are **never set by the
CLI** — they always fall back to the dataclass defaults. A user running
`personal-index health` cannot:

- raise/lower the `title_too_long` threshold (always 200 chars), or
- require more than one tag per item (`min_tags` is always 1, so a single tag
  satisfies `--require-tags` even when the user expects "at least N tags").

The checker-level behavior IS tested — `tests/deep/test_content_health_adversarial.py:152-155`
pins `min_tags=2` (`_checker(require_tags=True, min_tags=2)`), proving the
knob works at the `ContentHealthChecker` API. But **no CLI path can reach it**:
`tests/test_cli_health.py` has no test that drives `--min-tags` or
`--max-title-length` (they do not exist as options).

## Evidence

- `personal_index/cli_health.py:14-18` — the five `@click.option` lines (no
  `--max-title-length`, no `--min-tags`).
- `personal_index/cli_health.py:61-68` — `_build_config` sets 5 of 7 fields.
- `personal_index/content_health.py:194-202` — the 7-field `ContentHealthCheck`.
- `personal_index/content_health.py:308-321` — `_check_title_length` reads
  `self.config.max_title_length` (always 200 from the CLI).
- `personal_index/content_health.py:338-354` — `_check_tags` reads
  `self.config.min_tags` (always 1 from the CLI).
- `tests/deep/test_content_health_adversarial.py:152-155` — `min_tags=2` is
  pinned at the checker level (the knob works, but is unreachable via CLI).

## Proposed fix (implementer)

Add the two missing options to the `health` command and thread them through
`_build_config`, so all seven knobs are reachable:

1. `@click.option("--max-title-length", type=int, default=200, help="Maximum title length")`
2. `@click.option("--min-tags", type=int, default=1, help="Minimum tags per item (with --require-tags)")`
3. Extend `_build_config` to accept and set `max_title_length` and `min_tags`.

Defaults must match the dataclass defaults (200 and 1) so existing behavior is
unchanged when the new flags are omitted.

## Acceptance criteria

- `personal-index health --help` lists `--max-title-length` and `--min-tags`.
- Omitting both flags yields the same report as today (defaults 200 / 1).
- `--min-tags 2` with `--require-tags` flags a single-tagged item as
  `missing_tags` (mirrors the deep-test `min_tags=2` boundary).
- `--max-title-length 10` flags a title longer than 10 chars as
  `title_too_long`.

## Pinning tests to add (implementer — architect never writes tests/**)

In `tests/test_cli_health.py` (CLI surface, not the checker):

- **normal case:** a page with a 15-char title + `--max-title-length 10`
  produces a `title_too_long` issue in the output.
- **guard path:** the same page with the default (no `--max-title-length`)
  produces NO `title_too_long` issue (pins the default-200 behavior).
- **normal case:** `--require-tags --min-tags 2` on a single-tagged item
  produces a `missing_tags` issue.
- **guard path:** `--require-tags` (default `--min-tags 1`) on a single-tagged
  item produces NO `missing_tags` issue (pins the default-1 behavior).

## Docs update (same PR)

`docs/cli_health.md` (authored this cycle) already documents the five exposed
options and the known contract hole. On fix, update the `_build_config` row
and the "Known contract hole" section to reflect that all seven knobs are now
exposed.

## Self-review checklist (architect)

- [x] Component named: `personal_index/cli_health.py`.
- [x] Public contract stated: 5 exposed options vs 7 config fields; the two
      unexposed knobs (`max_title_length`, `min_tags`) and the checks they gate.
- [x] Behavior + error paths: empty-index guard, `require_score` derivation,
      `status_code` default 200.
- [x] Guard inputs named: default-200 / default-1 no-issue paths.
- [x] Acceptance criteria: 4 concrete, testable.
- [x] Pinning tests specified (normal + guard path each), implementer-owned.
- [x] Docs page in same PR: `docs/cli_health.md`.
- [x] Module confirmed WIRED (imported at `cli.py:27`, registered on `main`)
      before auditing its contract — this is a live command, not a dead
      parallel implementation.
