# TICKET-460: MarkdownExporter.export_item generic docstring (class-(b) doc-drift)

**File:** `personal_index/content_export/markdown_export.py`
**Function:** `MarkdownExporter.export_item` (line 21)
**Symptom:** One-line docstring `"""Export a single content item to Markdown."""` does not enumerate the conditional sections the body renders.
**Evidence:** Line 22: `"""Export a single content item to Markdown."""`
**Body performs:**
1. Renders `## {title}` heading (default "Untitled")
2. If `url` present: renders markdown link `[title](url)`
3. If `description` present: renders it as a paragraph
4. Renders tags section via `_render_tags` (skipped if no tags)
5. If `bookmarked` truthy: renders `*Bookmarked*`
6. If `score` is not None: renders `**Score:** {score:.2f}`
7. Renders metadata section via `_render_metadata` (skipped if no metadata)
**Fix:** Reword docstring to enumerate the conditional sections. NO behavior change. Add pinning test.
**Issue:** #761
**Status:** RESOLVED
