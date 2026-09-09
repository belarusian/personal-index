Status: OPEN
Kind: QA
Issue: #1160
Deep test: tests/deep/test_importer_adversarial.py (TestJsonNonDictItemContract, 2 xfail-strict)

# QA-8: importer._import_json — non-dict JSON array item crashes the whole import

## Symptom
`Importer._import_json(content, source)` crashes with an uncaught
`AttributeError` when a JSON **array** contains a non-dict item
(int / str / bool / float / null / list). The whole import aborts instead of
recording a per-item error and continuing to the next item.

The `_import_json` docstring explicitly promises:

    "A per-item ``ValueError``/``TypeError`` (raised during ``Bookmark``
    construction or ``manager.add``) is caught, appended to
    ``result.errors`` as ``"Error importing item: ..."`` and the loop
    continues to the next item rather than aborting."

The `except` clause only catches `(ValueError, TypeError)`. For a non-dict
item, `item.get("url", "")` raises `AttributeError`, which is NOT in the
except clause, so it propagates out of `import_from_content` and aborts the
entire import. A JSON array is a documented, supported input shape (the code
normalizes a top-level dict to a single-element list precisely so arrays are
handled uniformly), so a malformed item inside a valid array must be skipped
with an error, not crash the caller.

## Affected site
| module | function | line | idiom |
|--------|----------|------|-------|
| importer.py | `Importer._import_json` | ~146-158 | `for item in data: ... item.get("url", "")` with `except (ValueError, TypeError)` only |

## Exact repro
    python3 -c "
    from personal_index.importer import Importer
    from personal_index.bookmarks import BookmarkManager
    imp = Importer(BookmarkManager())
    try:
        r = imp.import_from_content('[{\"url\":\"http://a.com\"}, 42, {\"url\":\"http://b.com\"}]', 'json')
        print('OK imported=', r.total_imported, 'errors=', r.errors)
    except Exception as e:
        print('CRASH', type(e).__name__, e)
    "

## Observed output
    CRASH AttributeError 'int' object has no attribute 'get'

Same crash for every non-dict item type:
    string item -> CRASH AttributeError 'str' object has no attribute 'get'
    list item   -> CRASH AttributeError 'list' object has no attribute 'get'
    bool item   -> CRASH AttributeError 'bool' object has no attribute 'get'
    float item  -> CRASH AttributeError 'float' object has no attribute 'get'
    null item   -> CRASH AttributeError 'NoneType' object has no attribute 'get'

## Expected per docs/contract
Per the `_import_json` docstring, the bad item is recorded in
`result.errors` as `"Error importing item: ..."` and the loop continues, so
the two valid items are still imported:

    OK imported= 2 errors= ['Error importing item: ...']

## Deep test
tests/deep/test_importer_adversarial.py::TestJsonNonDictItemContract
(2 xfail-strict tests pin the correct contract; they flip to hard passes once
the loop guards non-dict items or the except clause also catches
AttributeError).
