Status: IMPLEMENTED #1051@a59f957 (cycle 179)
Kind: ARCH
Author: architect (cycle 174)
Issue: #1018

# ARCH-13: `cli.pipeline` `--steps` / `--no-*` flags are parsed but ignored

## Component
`personal_index.cli.pipeline` (cli.py, lines 670–715).

## Symptom
The `pipeline` command declares `--steps/-s`, `--no-crawl`, `--no-filter`,
`--no-score`, `--no-tag`, and `--no-index` (lines 680–686), and the function
signature binds `steps, no_crawl, no_filter, no_score, no_tag, no_index`
(lines 690–691), but **none of them is referenced in the body** (lines
692–715). The body only branches on `import_files` vs `urls` and always runs
the full pipeline via `runner.run_from_files` / `runner.run`. So a user
passing `--no-crawl` or `--steps filter,score` gets no effect — the flags are
silently ignored. This is a user-visible contract hole: the CLI advertises
stage-selection options that do nothing.

## Public contract (the code is the truth)
- `pipeline(ctx, urls, import_files, depth, max_pages, min_score,
  min_content_length, data_dir, steps, no_crawl, no_filter, no_score, no_tag,
  no_index, recursive)`.
- The body currently ignores `steps`, `no_crawl`, `no_filter`, `no_score`,
  `no_tag`, `no_index` and always runs every stage.

## Acceptance criteria
- Either the `--steps` / `--no-*` flags are implemented (the pipeline skips
  the stages named by `--no-*` / not named by `--steps`), OR the flags are
  removed from the command so the CLI does not advertise options that do
  nothing. Either way, `docs/cli.md` (the `pipeline` command entry + the
  contract-holes line) is updated to match the chosen resolution.
- After the change, passing `--no-crawl` (or `--steps`) either changes the
  stages that run, or the option no longer exists — it is never silently
  ignored.

## Pinning tests to add
`test_pipeline_no_crawl_flag_is_respected` — run `pipeline --import-file <f>
--no-crawl` (via the click `CliRunner`) and assert the crawl stage did not run
(e.g. `stats.pages_crawled == 0` or the crawler was not invoked), alongside a
normal run (`pipeline --import-file <f>`) asserting the crawl stage ran. One
test pins both the flag-respected path and the default path, so a regression
that re-introduces silently-ignored flags is caught. (If the resolution is to
remove the flags, the pinning test instead asserts the option is absent from
`pipeline --help`.)

## Docs page it updates
`docs/cli.md` (the `pipeline` command entry + the contract-holes line, which
this ticket resolves).
