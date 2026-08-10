# TICKET-90: Type error — `sitemap_builder.py` passes `dict[str, str]` to `Element(nsmap=...)` expecting `str`

## Title
`Element()` constructor called with `nsmap=NSMAP if NSMAP else {}` — mypy expects `nsmap: str` not `dict[str, str]`

## Evidence
File: `personal_index/sitemap_builder.py`
Line 75: `root = Element("urlset", nsmap=NSMAP if NSMAP else {})`
Line 83: `root = Element("sitemapindex", nsmap=NSMAP if NSMAP else {})`

mypy flags:
- Line 75: `Argument "nsmap" to "Element" has incompatible type "dict[str, str]"; expected "str"  [arg-type]`
- Line 83: `Argument "nsmap" to "Element" has incompatible type "dict[str, str]"; expected "str"  [arg-type]`

This is likely a mypy stub issue with `xml.etree.ElementTree.Element` — the actual `nsmap` parameter accepts `dict[str, str] | None`.

## Impact
False positive from mypy — runtime behavior is correct. However, it creates noise in type checking output.

## Suggestion
Add a `# type: ignore[arg-type]` comment to suppress the false positive, or use `cast()` to work around the stub limitation. Alternatively, upgrade mypy stubs if a newer version fixes this.
