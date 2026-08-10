# TICKET-107: Mypy type error — Missing stubs for external libraries

## Title
Mypy cannot find type stubs for several external dependencies

## Evidence
Mypy reports "Library stubs not installed" errors for:
- `defusedxml.ElementTree` (lines in `sitemap.py`, `rss.py`)
- `requests` (lines in `content_health.py`, `crawler/__init__.py`, `crawler/main.py`)
- `yaml` (line in `config/loader.py`)

## Impact
- Type checking incomplete for external library usage
- Potential runtime type errors not caught

## Suggestion
Install type stub packages:
