Status: VERIFIED (validator cycle 157: pinning test test_config_show_uses_loader_load_config passes + docs/cli.md load_config entry removed; adversarial: config show reflects loader values)
Kind: ARCH
Author: architect (cycle 174)
Issue: #1017

# ARCH-12: `cli.load_config` (module-level) is dead code

## Component
`personal_index.cli.load_config` (cli.py, line 50).

## Symptom
The module-level `load_config(data_dir) -> dict` (line 50) is defined but
**never called** anywhere in the module or the repo (verified: the `config`
subcommands import `personal_index.config.loader.load_config` at lines 1236,
1269, 1301 — a different function). It also ignores its `data_dir` argument
(hardcodes `config.yaml`, line 51). A reader would reasonably assume
`load_config` is the config loader used by the CLI, but it is dead.

## Public contract (the code is the truth)
- The config loader actually used by the `config` subcommands is
  `personal_index.config.loader.load_config` (imported locally in
  `config_show`, `config_set_crawler`, `config_set_schedule`).
- The module-level `cli.load_config` is not referenced by any code path.

## Acceptance criteria
- The module-level `load_config` is removed (it is dead), OR — if the operator
  prefers to keep it — it is wired into a live path (e.g. the `config`
  subcommands use it) so there is one config loader, not two. Either way,
  `docs/cli.md` "Bootstrap / data-dir + config path" is updated to match the
  chosen resolution (remove the `load_config` entry, or reword it to state
  which loader is live).
- After the change there is exactly ONE config loader used by the CLI.

## Pinning tests to add
`test_config_show_uses_loader_load_config` — run `config show` (via the click
`CliRunner`) against a temp `config.yaml` and assert the output reflects the
loaded config (e.g. the data dir / crawler values). This pins that the live
config path goes through `personal_index.config.loader.load_config`, so a
regression that re-introduces a dead/alternate module-level loader is caught.

## Docs page it updates
`docs/cli.md` (the `load_config` bootstrap entry + the contract-holes line,
which this ticket resolves).
