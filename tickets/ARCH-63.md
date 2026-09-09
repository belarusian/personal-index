Status: OPEN
Kind: ARCH
Author: architect (cycle 228)
Issue: #1215

# ARCH-63: CONTRACT RULE — defensive `_load` must degrade to empty state on ANY malformed value (kill the defensive-load-crash CLASS)

## Component
Cross-cutting contract rule for `personal_index/**` (home: `docs/CONTRACTS.md`).
This is a CLASS ticket, not a single-site fix: the same defect recurs across
at least two modules and must be killed once, at the contract level.

## The class (why a single ticket)
The defensive-load-crash defect has now been found independently in TWO sites,
each ticketed on its own:

| Site | Method | Per-value construction | except tuple | Crash on non-dict value |
|------|--------|------------------------|--------------|--------------------------|
| `domains.py` | `DomainManager._load` | `DomainRule.from_dict(r)` | `(json.JSONDecodeError, KeyError)` | `TypeError` (from `from_dict`) |
| `content_pin.py` | `ContentPinner._load` | `item_data.get("pinned_at", ...)` | `(json.JSONDecodeError, KeyError, TypeError)` | `AttributeError` (from `.get`) |

Every one of these `_load` methods rebuilds in-memory state from a persisted
JSON mapping: it `json.load`s the file, checks `isinstance(data, dict)`, then
iterates `data.items()` and constructs a per-key object from each value
(`DomainRule.from_dict(r)` / `PinnedItem(... item_data.get(...))`). The
defensive contract is to reset to the empty state (`self._rules = {}` /
`self._pinned = {}`) on a malformed file. But the `except` tuple enumerates
only the exception types the author happened to anticipate. A value that is
valid JSON but NOT a mapping (e.g. `{"a": "notadict"}`) makes the per-value
construction raise a DIFFERENT type — `TypeError` in `domains` (not in its
tuple) or `AttributeError` in `content_pin` (not in its tuple) — which
propagates out of `__init__`/`__post_init__` and fails the WHOLE object
construction instead of degrading gracefully. The defect is the same shape in
every site; fixing each site in isolation is whack-a-mole.

This is a DISTINCT class from:
- the **persistence-atomicity** class (ARCH-44 content-pin, ARCH-46
  content-versioning, ARCH-40 storage) — that class is about a non-atomic
  `_save` corrupting the file; this class is about a `_load` that crashes on a
  well-formed-but-wrong-shape value.
- the **negative-slice-truncation** class (ARCH-17) — unrelated.

## Public contract (the rule)
Add to `docs/CONTRACTS.md` a binding rule for every private `_load` method
whose contract is "rebuild in-memory state from a persisted JSON mapping"
(i.e. any method that `json.load`s a file, checks `isinstance(data, dict)`,
and iterates `data.items()` constructing a per-key object from each value):

> **Defensive-load guard (binding).** Any `_load` method that rebuilds
> in-memory state from a persisted JSON mapping MUST degrade to the empty
> state on ANY malformed value — a value that is not a mapping, or a mapping
> whose fields have the wrong type — not only on the specific exception types
> it enumerates. A malformed value is out-of-range and must yield the same
> empty state as a missing file; construction MUST NOT raise. The guard is
> stated in the method's contract docstring (part 1, guard paths) and
> witnessed by ONE pinning test that asserts the constructed state for a
> non-dict value (== empty state) ALONGSIDE the normal case.

Mechanism is the implementer's choice (broaden the `except` tuple to cover the
value-shape errors the per-value construction can raise — `AttributeError`,
`TypeError`, `KeyError`, `ValueError` — or wrap the per-value construction so a
malformed value degrades that value / the whole store to empty). The binding
obligation is the OBSERVABLE behavior: a well-formed-but-wrong-shape value
yields the empty state and never propagates out of construction.

## Acceptance criteria
1. `docs/CONTRACTS.md` carries the defensive-load guard rule (above), in a
   section that is discoverable from the "How to apply" list.
2. Each of the two sites above gets the guard so the code matches the contract
   (implementer work — see "Scope split"): a non-dict value in the persisted
   mapping yields the empty state and does NOT raise out of construction.
3. Each site's pinning test asserts the constructed state for a non-dict value
   (== empty state) AND the normal case (== the expected populated state), so
   one test pins the guard (implementer work).
4. The existing per-site tickets (QA-11, QA-17) are cross-referenced from this
   ticket as the instances the class rule subsumes; they remain OPEN until
   their code guard lands (validator's duty to close).

## Scope split (architect vs implementer)
- **Architect (this ticket, docs/ + ticket only):** write the rule into
  `docs/CONTRACTS.md` (new "Defensive-load guard (binding)" section + a
  "How to apply" step), and file this ARCH ticket.
- **Implementer (separate PR, claims this ticket):** add the guard to
  `domains.py` `DomainManager._load` and `content_pin.py`
  `ContentPinner._load`, add the two pinning tests, and update the two
  per-site docs pages (`content-pin.md` already names the hole; `domains`
  page) to state the corrected guard path.

## Pinning tests (to be added by the implementer)
- `domains`: write a rules file `{"example.com": "notadict"}` (a non-dict
  value), construct `DomainManager(rules_file=...)`, assert construction does
  NOT raise and `manager.list_rules()` (or the equivalent accessor) == `[]`
  (empty state); alongside the normal case (a valid rule -> populated).
- `content_pin`: write a storage file `{"a": "notadict"}` (a non-dict value),
  construct `ContentPinner(storage_path=...)`, assert construction does NOT
  raise and the pinner's in-memory state is empty (e.g. `pin`/`unpin`/list
  accessors reflect no pinned items); alongside the normal case (a valid
  pinned item -> populated).
