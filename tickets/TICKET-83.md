# TICKET-83: Type error — `FeedItem.from_dict()` can pass empty string `''` to `datetime | None` fields

## Title
`FeedItem.from_dict()` passes `Literal['']` to `published`/`updated` which expect `datetime | None`

## Evidence
File: `personal_index/content_feed.py`
Lines 77-78:
