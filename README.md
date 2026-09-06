# Personal Index

A personal web search engine that scans, filters, and indexes the web based on your interests.

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/belarusian/personal-index)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)

## Overview

Personal Index lets you:

- **Crawl** websites and follow links
- **Extract** content from HTML pages
- **Filter** based on your interests and rules
- **Score** pages by relevance
- **Tag** pages with keywords
- **Index** for full-text search
- **Search** across your indexed content

## Quick Start

### 1. Install

Requires Python 3.10+.

```bash
git clone https://github.com/belarusian/personal-index.git
cd personal-index
pip install -e .
```

This installs the `personal-index` console script (declared in
`pyproject.toml` as `personal-index = "personal_index.cli:main"`). You can
also run it as a module: `python3 -m personal_index`.

### 2. Initialize

Create a data directory and a default `config.yaml`:

```bash
personal-index init
```

This creates `.personal_index/` (with `cache/`, `archive/`, `backups/`) and
writes a default `config.yaml` if one does not already exist.

### 3. Declare your interests

```bash
personal-index interests add programming --keywords "python,javascript,web"
```

### 4. Run the pipeline

Crawl, filter, score, tag, and index in one step:

```bash
personal-index pipeline https://example.com
```

### 5. Search

```bash
personal-index search "python"
```

## Command Reference

Run `personal-index --help` for the full list, or `personal-index <command> --help`
for a command's options. Global options: `--data-dir TEXT` (default
.personal_index), `-v/--verbose`, `--version`.

| Command | Purpose |
| --- | --- |
| `init` | Initialize a new data directory and default config |
| `interests` | Manage content interests (`add`, `list`, `remove`) |
| `tags` | Manage content tags (`add`, `list`, `remove`) |
| `import` | Import local files/directories into the index (`-r/--recursive`) |
| `crawl` | Crawl a URL and extract content (`-d/--depth`, `-m/--max-pages`) |
| `pipeline` | Run the full crawl, filter, score, tag, index pipeline |
| `search` | Search indexed content (`-n/--limit`, `--tag`, `--format`, `--json`) |
| `export` | Export indexed content (`--format`, `--output`) |
| `status` | Show status of your personal-index |
| `stats` | Show statistics (`--format`) |
| `list` | List all indexed pages (`--format`, `--limit`, `--sort`) |
| `top` | Show the highest-scored pages (`--format`, `--limit`) |
| `remove` | Remove a page from the index by URL |
| `clear` | Clear index data (`--index`, `--tags`, `--interests`) |
| `doctor` | Diagnose setup issues |
| `verify` | Verify data integrity (`--quick`) |
| `watch` | Watch files/dirs for changes and re-index (`-i/--interval`, `--once`) |
| `schedule` | Manage scheduled crawl jobs (`add`, `list`, `remove`, `run`) |
| `config` | Manage configuration (`show`, `set-crawler`, `set-schedule`) |
| `dedup` | Find and remove duplicate content |
| `health` | Check the health of indexed content |
| `recommend` | Get recommendations from a query or seed content |

### Pipeline options

`pipeline` accepts `URLS...` and, for local imports, `-i/--import-file` (repeatable,
`-r/--recursive` for directories). Stage control: `--no-crawl`, `--no-filter`,
`--no-score`, `--no-tag`, `--no-index`, or `-s/--steps` (comma-separated subset).
Thresholds: `--min-score`, `-l/--min-content-length`. Crawl bounds: `-d/--depth`,
`-m/--max-pages`.

## Configuration

Configuration lives in `config.yaml` (created by `personal-index init`). A fully
commented reference is in [`config.sample.yaml`](config.sample.yaml). Top-level keys:

- `data_dir` - where index data is stored (default `.personal_index`)
- `crawler` - `max_depth`, `max_pages_per_domain`, `timeout`, `politeness_delay`
- `index` - index settings
- `pipeline` - `min_score_threshold`, `min_content_length`
- `scheduler` - default schedule interval / enabled
- `notifications` - notification settings
- `export` - export defaults
- `interests` - list of interest entries
- `log_level` - logging verbosity (default `INFO`)

Inspect and edit at runtime with `personal-index config show`,
`personal-index config set-crawler ...`, and `personal-index config set-schedule ...`.

## Project Structure

- `personal_index/` - the package. `cli.py` is the CLI entry point; `cli_*.py`
  hold the `dedup`, `health`, `recommend`, `export`, `top`, and `verify`
  subcommands. `content_api.py` serves the `/api/v1/content` HTTP routes.
- `tests/` - the test suite (run with `python3 -m pytest tests/ -q`).
- `config.yaml` / `config.sample.yaml` - live and reference configuration.
- `pyproject.toml` - packaging, dependencies, and the `personal-index` console script.
