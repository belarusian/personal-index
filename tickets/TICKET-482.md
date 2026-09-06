# TICKET-482: _extract_title drops title text when <title> contains inline markup

## File
personal_index/content.py, line 66 (_extract_title)

## Symptom
_extract_title uses `tag.string.strip()`. BeautifulSoup's `tag.string` returns
None when the tag has more than one child node (i.e., any inline markup such as
`<title>Hello <b>World</b></title>`), so the function silently returns "" and
the title text is lost from ExtractedContent.title, get_searchable_text(), and
any downstream search/indexing that relies on the title.

## EvidenceIssue: #815
RESOLVED
