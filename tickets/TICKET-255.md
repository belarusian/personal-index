# TICKET-255: TagStore.remove_tag_from_page returns True when the tag was not on the page

Status: OPEN
Module: personal_index/tags.py
Symptom: `remove_tag_from_page(url, tag_name)` returns `True` whenever `url` is
present in `_page_tags`, even if `tag_name` was never associated with that page.
Consequently the CLI `tags remove <tag> <url>` (cli.py:249) prints
"Removed tag '<tag>' from <url>" for a tag that was not actually present,
misreporting a no-op as a success.
Evidence: tags.py:128-134
    def remove_tag_from_page(self, url, tag_name):
        if url not in self._page_tags:
            return False
        self._page_tags[url].discard(tag_name)   # discard is a no-op if absent
        self._save()
        return True                              # True even when nothing removed
Existing test test_e2e_edge_cases.py:262 only covers the URL-absent case
(returns False); the tag-absent-but-URL-present case is untested and wrong.
Minimal additive fix: capture whether the tag was actually present before
discarding; return that boolean. Only save when something changed.
    present = tag_name in self._page_tags.get(url, set())
    if present:
        self._page_tags[url].discard(tag_name)
        self._save()
    return present
Issue: #339
