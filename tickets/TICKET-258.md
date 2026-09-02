# TICKET-258: Interest.matches aborts on a single malformed url_pattern (false negative)

Status: OPEN
Module: personal_index/models.py (Interest.matches) - exercised by personal_index/interests.py matches_any
Issue: #345

## Symptom
`Interest.matches(text, url)` returns `False` as soon as it hits ONE malformed
regex in `url_patterns`, even when a LATER valid pattern would match the URL.
This is a false negative: a single bad pattern poisons the whole match.

## Evidence (line numbers)
- personal_index/models.py:104  `for pattern in self.url_patterns:`
- personal_index/models.py:112  `if re.search(pattern, url, re.IGNORECASE):`
- personal_index/models.py:114  `except re.error:`
- personal_index/models.py:115  `return False`   <-- aborts the entire method

Runtime repro (confirmed):
    i  = Interest(name='x', url_patterns=['[bad-regex', 'example.com'])
    i.matches('text', 'example.com')  -> False   (should be True)
    i2 = Interest(name='y', url_patterns=['example.com'])
    i2.matches('text', 'example.com') -> True    (control)

`interests.py` `matches_any` (line ~129) delegates to `Interest.matches`, so a
store with one malformed pattern silently drops every URL that would otherwise
match via a later pattern.

## Minimal additive fix
In the `except re.error` handler, skip just the offending pattern and continue
the loop instead of returning False:
    except re.error:
        continue
This preserves the existing behavior for valid patterns and only changes the
malformed-pattern case from "abort -> False" to "skip -> keep checking".
Add a regression test asserting a valid pattern still matches when an earlier
pattern is malformed.
