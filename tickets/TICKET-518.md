# TICKET-518: README.md truncated — no install/launch/usage instructions

Status: OPEN (in progress on build139/readme-quick-start-518)

## File
README.md

## Symptom
The main README is truncated at 623 bytes. It ends at the heading
"## Quick Start" with nothing after it — no installation steps, no
launch instructions, no command reference. A user cloning the repo
cannot tell how to install or launch the project.

## Evidence
- `wc -c README.md` -> 623 bytes
- `tail -c 120 README.md` ends at "## Quick Start\n" (no body)
- `python3 -m personal_index --help` works and lists 24 commands
  (init, interests, tags, import, crawl, pipeline, search, export,
  status, stats, list, top, remove, clear, doctor, verify, watch,
  schedule, config, dedup, health, recommend) — none documented.
- pyproject.toml declares the console script
  `personal-index = "personal_index.cli:main"` and dependencies,
  but the README never mentions `pip install -e .` or the entry point.

## Minimal additive fix
Complete the README: keep the existing Overview, then add real
Quick Start (install via `pip install -e .` + first-run init/interests/
pipeline/search), a command reference table for the 22 top-level CLI
commands (verified against `python3 -m personal_index --help` and
personal_index/cli.py), a pipeline-options subsection, a configuration
section (config.yaml / config.sample.yaml top-level keys), and a
project-structure pointer. Additive only — do not remove existing content.
Landed: README.md 623 -> 4825 bytes.

## Issue
Issue: #897
