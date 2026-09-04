# TICKET-376: _extract_links includes spurious self-link for empty href

Status: RESOLVED
Issue: #590
Module: personal_index/content.py
Function: _extract_links (line 93)
Defect class: (a) behavioral

## Symptom
`<a href="">` (empty href, common in HTML for placeholder/JS-driven links)
resolves to the page's own URL via `resolve_relative_url(base_url, "")`,
adding a self-referential link to the extracted links list. In a personal
index, self-links are noise — they don't represent a connection to another
page.

## Evidence