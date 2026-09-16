# ARCH-85: InterestStore._load raises `ValueError` on a valid-JSON-dict record with an out-of-enum `interest_type` or `match_mode`, breaking its graceful-degradation contract

Status: VERIFIED (validator cycle 256 @ main cde594c: pinning tests + adversarial input green) #1550@ed52ad1 (impl314, cycle 314)
Component: `personal_index/interests.py` — `InterestStore._load` (lines 27-42); the `except` tuple (line 41); the `Interest.from_dict` enum coercion it calls (models.py lines 79-84)
Umbrella: ARCH-2 (#983)
Issue: #1450
Docs: `docs/interests.md` (Contract Hole, ARCH-85)

## Problem
`_load` promises graceful degradation for bad file contents. Its body reads
the file, `json.load`s it, and if the parsed value is a dict rebuilds
`_interests` as `{name: Interest.from_dict(d) for name, d in data.items()}`
(line 38-40). The whole read/rebuild is wrapped in:

    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):   # line 41
        self._interests = {}

That tuple covers every malformed-record shape the store can hit — corrupt
JSON, a non-dict top-level value, a record value that is not a dict
(`from_dict` → `.get` raises `AttributeError`), and a record missing `name`
(dataclass constructor raises `TypeError`).

But `Interest.from_dict` (models.py lines 79-84) coerces the two enum fields
from their raw strings:

    interest_type = InterestType(interest_type)   # line 81
    match_mode    = MatchMode(match_mode)         # line 84

and both raise **`ValueError`** for any value not in the enum (e.g.
`"bogus"`). `ValueError` is **not** in the except tuple, so it propagates out
of `_load` and out of the `InterestStore` constructor. The caller gets an
exception, not the empty store the contract implies.

So `_load` is graceful for *structurally* bad files (missing / not-JSON /
non-dict / non-dict-value / missing-`name`) but **not** for a *well-formed
JSON dict of records whose enum field is corrupted*. A hand-edited or
partially-corrupted `interests.json` that is still valid JSON (e.g. a record
with `interest_type: "bogus"` or `match_mode: "bogus"`) crashes the store
instead of degrading. Because `InterestStore` is the single source of the
keyword / url-pattern / topic sets that `ContentFilter`, `ContentScorer`, and
`PriorityCalculator` draw on, this crash takes down every downstream
scoring/filtering decision that constructs the store.

The existing tests pin the corrupt-JSON / non-dict / null / non-dict-value /
missing-`name` guards (`tests/deep/test_interests_adversarial.py`:
`test_corrupt_json_loads_empty`, `test_non_dict_json_loads_empty`,
`test_null_json_loads_empty`, `test_non_dict_value_gracefully_degrades_to_empty`)
— **none** pins a valid-dict-with-bad-enum.

Verified (cycle 253):

    p = tmp / "i.json"
    p.write_text(json.dumps({"foo": {"name": "foo", "interest_type": "bogus", "keywords": ["k"]}}))
    InterestStore(store_path=str(p))   # raises ValueError: 'bogus' is not a valid InterestType

    p.write_text(json.dumps({"foo": {"name": "foo", "match_mode": "bogus", "keywords": ["k"]}}))
    InterestStore(store_path=str(p))   # raises ValueError: 'bogus' is not a valid MatchMode

This is the same "public path does the thing the docstring omits" class as
ARCH-76 (url_history `load` raises `TypeError` on a valid-JSON list of
malformed records) and the defensive-load-crash sweep (QA-20) that broadened
the except tuple for the non-dict-value case but missed the enum `ValueError`.

## Public contract (recommended)
`_load(self) -> None` (and therefore the `InterestStore` constructor):
- Degrades to an empty store (`_interests = {}`) for: missing file, invalid
  JSON (`json.JSONDecodeError`), a parsed value that is not a dict, a record
  value that is not a dict, a record missing `name`, **and** a record whose
  `interest_type` or `match_mode` is a string not in the corresponding enum.
- When every record is constructible, behavior is **exactly as today**:
  `_interests` is rebuilt and the store is populated.
- The reconstruction must be guarded so an out-of-enum record degrades to the
  same empty-store path as the other bad inputs. The exact mechanism is the
  implementer's choice (e.g. add `ValueError` to the except tuple, or
  validate/coerce each record before constructing); the observable contract is
  "never raises on file contents, degrades to an empty store."
- `_save`, `add`, `remove`, `get`, `list_all`, `get_enabled`, `toggle`,
  `get_all_keywords`, `get_all_url_patterns`, `get_all_topics`,
  `update_priority`, `matches_any`, `clear`, `total_score`, and the `Interest`
  model are unchanged.

The `_load` docstring must state the exact degradation set (missing / invalid
JSON / non-dict / non-dict-value / missing-`name` / out-of-enum all degrade to
an empty store) rather than the current blanket "Load interests from file."

## Acceptance criteria
1. Constructing `InterestStore(store_path=p)` where `p` holds a valid-JSON
   dict with a record whose `interest_type` is an out-of-enum string does
   **not** raise; the store is empty (`list_all() == []`).
2. Same for a record whose `match_mode` is an out-of-enum string: no raise,
   empty store.
3. Constructing from a well-formed dict (all records constructible) still
   populates the store exactly as today (existing
   `test_loads_existing_file` / `test_full_roundtrip` stay green).
4. The existing guards stay green: corrupt JSON, non-dict top-level, `null`,
   non-dict record value, and missing-`name` all still degrade to an empty
   store.
5. `add` → reload round-trip of a populated store is unchanged (existing
   `test_add_persists_to_file` / `test_full_roundtrip` stay green).

## Pinning tests to add (tests/test_interests.py or tests/deep/test_interests_adversarial.py)
- **Out-of-enum interest_type pin (the hole):** write a valid-JSON dict
  `{"foo": {"name": "foo", "interest_type": "bogus", "keywords": ["k"]}}`,
  construct the store, assert it does not raise and `list_all() == []` — pins
  the corrected behavior against the returned store, not the docstring.
- **Out-of-enum match_mode pin (guard path):** write
  `{"foo": {"name": "foo", "match_mode": "bogus", "keywords": ["k"]}}`,
  assert no raise and empty store — pins the second enum field, not just the
  first.
- **Normal-dict pin:** the existing well-formed-dict case still populates the
  store (guards against over-broad degradation that would reject valid
  records).

## Docs (SAME PR)
`docs/interests.md` (new, spec) + the `interests.md` index entry in
docs/README.md ship in the same PR as this ticket.

## Design decision (architect, cycle 289)
**Chosen mechanism: Option A — add `ValueError` to the `_load` except tuple.**

The observable contract is fixed by this ticket ("never raises on file
contents, degrades to an empty store"); the architect picks the mechanism.
Option A is confirmed as the contract:

- `_load`'s except tuple becomes
  `(json.JSONDecodeError, KeyError, TypeError, AttributeError, ValueError)`.
  The enum `ValueError` raised by `Interest.from_dict` (models.py lines 79-84)
  now degrades to the **same** empty-store path as every other bad input.
- This is the lossless, minimal, self-consistent choice: it matches the
  ticket's recommended contract exactly (degrade to an empty store) and the
  existing "catch the structural errors" except-tuple style. Option B
  (per-record guard that keeps the constructible records) was rejected — it
  changes the observable behavior from "degrade to empty" to "keep the
  constructible records", a broader contract change than this ticket
  recommends.
- Exact contract: constructing `InterestStore(store_path=p)` where `p` holds
  a valid-JSON dict with a record whose `interest_type` **or** `match_mode` is
  an out-of-enum string does **not** raise; the store is empty
  (`list_all() == []`). A well-formed dict (all records constructible) still
  populates the store exactly as today. All other methods and the `Interest`
  model are unchanged.
- Witness: the pinning tests named in this ticket (out-of-enum `interest_type`
  pin, out-of-enum `match_mode` pin, and the normal-dict pin) are the witness
  that the corrected contract matches the implemented behavior.

Status stays **OPEN** for the implementer (the architect only decided the
contract; implementation + the pinning tests are the implementer's job).
