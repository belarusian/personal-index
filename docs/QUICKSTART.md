# Quick Start Guide

Get up and running with Personal Index in 5 minutes.

## Step 1: Install

```bash
pip install personal-index
```

## Step 2: Initialize

```bash
personal-index init
```

This creates:
- `.personal_index/` data directory
- `config.yaml` configuration file

## Step 3: Add Interests

Tell Personal Index what you care about:

```bash
personal-index interests add -n programming -k python -k javascript -k rust
personal-index interests add -n devops -k docker -k kubernetes -k ci-cd
```

## Step 4: Import Content

### From local files:

```bash
personal-index pipeline --import-file ./my-articles/ --recursive
```

### From the web:

```bash
personal-index pipeline https://example.com
```

## Step 5: Search

```bash
personal-index search "python async"
personal-index search "docker compose"
```

## Step 6: Export

```bash
personal-index export --format markdown
personal-index export --format json
personal-index export --format csv
```

## What Happened?

Your content went through the full pipeline:

1. **Crawl** - Files were read (or URLs fetched)
2. **Extract** - Text was extracted from HTML/Markdown
3. **Filter** - Short/low-quality content was filtered out
4. **Score** - Content was scored based on your interests
5. **Tag** - Topics were auto-detected and tagged
6. **Index** - Everything was added to the search index

## Next Steps

- Run `personal-index stats` to see your index statistics
- Run `personal-index top` to see your highest-scored content
- Run `personal-index doctor` to check system health
- Edit `config.yaml` to customize behavior
