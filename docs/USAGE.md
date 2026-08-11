# Personal Index - Usage Guide

## Commands Overview

### Main Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize a new project |
| `interests` | Manage interests |
| `tags` | Manage tags |
| `pipeline` | Run the full pipeline |
| `search` | Search indexed content |
| `export` | Export indexed content |

### Interest Commands

| Command | Description |
|---------|-------------|
| `interests add -n NAME -k KEYWORD` | Add a new interest |
| `interests list` | List all interests |
| `interests remove NAME` | Remove an interest |

### Tag Commands

| Command | Description |
|---------|-------------|
| `tags add TAGNAME FILE` | Add a tag to a file |
| `tags list` | List all tags |
| `tags remove TAGNAME FILE` | Remove a tag from a file |

### Pipeline Options

| Option | Description |
|--------|-------------|
| `-i, --import-file FILE` | Import local files instead of crawling |
| `-d, --depth N` | Max crawl depth (default: 3) |
| `-m, --max-pages N` | Max pages to crawl (default: 100) |

### Search Options

| Option | Description |
|--------|-------------|
| `--limit N` | Maximum results (default: 20) |
| `--tag NAME` | Filter by tag |
| `--format FORMAT` | Output format (text, json, csv) |

### Export Options

| Option | Description |
|--------|-------------|
| `--format FORMAT` | Output format (markdown, json, csv) |
