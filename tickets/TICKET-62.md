# TICKET-62: XML parsing vulnerability — ET.fromstring() used on untrusted data in 5 locations

## Title
`xml.etree.ElementTree.fromstring()` used to parse untrusted XML/HTML data

## Evidence
ruff S314 flags 5 locations where `ET.fromstring()` parses potentially untrusted data:

1. `personal_index/importer.py:151` — HTML/XML import
2. `personal_index/importer.py:194` — XML import
3. `personal_index/importer.py:229` — OPML import
4. `personal_index/rss.py:70` — RSS feed parsing
5. `personal_index/sitemap.py:60` — Sitemap parsing

Example from `personal_index/importer.py:151`:
