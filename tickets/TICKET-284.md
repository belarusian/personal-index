# TICKET-284: search_suggestions to_dict/from_dict alias live lists

- Status: OPEN
- Issue: #393
- Module: personal_index/search_suggestions.py
- Class: logic (shared mutable reference between serialized dict and live instance / input)

## Symptom
`SearchSuggestions.to_dict` (line 364) returns the LIVE internal lists by reference:
`"search_history": self._search_history`, `"tags": self._tags`, `"keywords": self._keywords`
(lines 378-380). A caller that mutates the returned dict's lists mutates the instance.

Conversely `from_dict` (line 382) assigns the input lists by reference:
`instance._search_history = data.get("search_history", [])` (line 388) and likewise for
tags/keywords (lines 389-390). The deserialized instance shares list objects with the
caller's `data` dict, so later mutation of either side leaks into the other.

## Evidence
- personal_index/search_suggestions.py:378  `"search_history": self._search_history,`  <- live list by reference
- personal_index/search_suggestions.py:379  `"tags": self._tags,`
- personal_index/search_suggestions.py:380  `"keywords": self._keywords,`
- personal_index/search_suggestions.py:388  `instance._search_history = data.get("search_history", [])`  <- input list by reference
- personal_index/search_suggestions.py:389  `instance._tags = data.get("tags", [])`
- personal_index/search_suggestions.py:390  `instance._keywords = data.get("keywords", [])`

## Minimal additive fix
- `to_dict`: return copies — `list(self._search_history)`, `list(self._tags)`, `list(self._keywords)`.
- `from_dict`: assign copies — `list(data.get("search_history", []))` etc.

## Regression tests (tests/test_search_suggestions.py)
- mutating the dict returned by to_dict does not change the instance's lists.
- mutating the input dict passed to from_dict does not change the instance's lists.
