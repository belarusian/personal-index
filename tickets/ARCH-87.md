# ARCH-87: `UrlFilterRule.is_blacklist` is a public field the filtering logic never reads — a "public field does nothing" contract hole

Status: OPEN
Component: `personal_index/url_filter.py` — `UrlFilterRule.is_blacklist` (line 14); the two `is_blacklist=` writes in `add_blacklist` (line 49) and `add_whitelist` (line 53); the decision methods `is_allowed` (lines 55-69) and `get_matching_rule` (lines 104-128) which decide block/allow purely by list membership
Umbrella: ARCH-2 (#983)
Issue: #1463
Docs: `docs/url_filter.md` (Contract Hole, ARCH-87)

## Problem
`UrlFilterRule` is a `@dataclass` with three public fields:

    pattern: str            # line 13
    is_blacklist: bool = True   # line 14
    description: str = ""   # line 15

`is_blacklist` is accepted and written, but is **never read anywhere in the
module** — `grep -rn is_blacklist personal_index/ --include='*.py'` returns
exactly three lines, all **writes**:

    line 14:  is_blacklist: bool = True          # declaration
    line 49:  ...is_blacklist=True, ...          # add_blacklist
    line 53:  ...is_blacklist=False, ...         # add_whitelist

The block/allow decision is made **purely by list membership**: a rule is a
whitelist rule iff it sits in `self._whitelist` (line 41), and a blacklist rule
iff it sits in `self._blacklist` (line 40). `is_allowed` (lines 65-69) scans
`_whitelist` first, then returns `all(not rule.matches(url) for rule in
self._blacklist)`; `get_matching_rule` (lines 121-128) scans `_whitelist` then
`_blacklist`. Neither inspects `rule.is_blacklist`. So the field is **redundant
with list membership** and cannot route a rule: a `UrlFilterRule` appended to
`_blacklist` with `is_blacklist=False` still behaves as a blacklist rule,
because the list — not the field — decides. The `True` default (line 14) is
also **unreachable via the public API**: both `add_blacklist` and
`add_whitelist` pass an explicit `is_blacklist`, so a caller can never observe
the default through the documented surface.

The hole is **masked by the tests**: `tests/test_url_filter.py`
(`test_whitelist_returned_when_both_match`, line 144;
`test_blacklist_returned_when_no_whitelist_match`, line 151) assert
`rule.is_blacklist is False` / `is True` on the object returned by
`get_matching_rule`. Those assertions pass because the field is *written*
correctly by the add_* methods — but they do not exercise the field as a
*decision input*, so the suite stays green whether or not the field is ever
read. This is the same "public field does nothing" class as ARCH-86
(`StatsCollector.interest_store`).

## Public contract (recommended)
Pick **ONE** resolution and state it as the public contract. The recommended
resolution is **(a) remove the dead field**:

- Remove the `is_blacklist` field from `UrlFilterRule` (line 14).
  `UrlFilterRule` then has exactly two fields, `pattern` and `description`, and
  its constructor is `UrlFilterRule(pattern, description=...)`.
- Remove the `is_blacklist=` keyword argument from `add_blacklist` (line 49)
  and `add_whitelist` (line 53).
- All decision behavior is **exactly as today**: `is_allowed` / `is_blocked` /
  `filter_urls` / `get_blocked_urls` / `get_matching_rule` never read the
  field, so nothing about the returned values changes; only the dead public
  surface goes.
- The `UrlFilterRule` docstring (line 12) and the `get_matching_rule`
  docstring (lines 105-120) must state that block/allow is decided by
  **list membership** (whitelist list vs blacklist list), not by a per-rule
  flag — so the reader is not led to believe the field routes a rule.

Resolution **(b)** — make `is_blacklist` the actual routing key (e.g. a single
`_rules` list where `is_allowed` consults `rule.is_blacklist`) — is the
alternative; it is a behavior change and is NOT recommended because it would
restructure the two-list invariant the existing `tests/test_url_filter.py` and
`tests/deep/test_url_filter_adversarial.py` suites pin. If (b) is chosen, the
ticket must restate the exact new data layout and the pinning tests that
change. **The implementer must not do both.**

## Acceptance criteria
1. After resolution (a): `UrlFilterRule` has no `is_blacklist` field;
   constructing it with `is_blacklist=...` raises `TypeError` (unexpected
   keyword) — the dead surface is gone.
2. `add_blacklist` / `add_whitelist` no longer pass `is_blacklist`; a rule
   added via `add_whitelist` is still returned by `get_matching_rule` and
   still takes precedence over a matching blacklist rule (existing
   `test_whitelist_returned_when_both_match` /
   `test_blacklist_returned_when_no_whitelist_match` stay green, updated to the
   new field set).
3. `is_allowed` / `is_blocked` / `filter_urls` / `get_blocked_urls` return the
   **same** values as today for the same rule set (all existing
   `tests/test_url_filter.py` and `tests/deep/test_url_filter_adversarial.py`
   assertions on returned values stay green).
4. The empty-filter guard path still returns `True` from `is_allowed` (no
   rules -> allowed) and `None` from `get_matching_rule` (existing guard-path
   tests stay green).
5. The `docs/url_filter.md` "Contract hole (ARCH-87)" section is updated to
   reflect the resolved contract (dead field removed) in the SAME PR.

## Pinning tests to add (tests/test_url_filter.py)
- **Dead-field-removed pin (the hole):** assert `UrlFilterRule` no longer
  accepts `is_blacklist` — `inspect.signature(UrlFilterRule)` has no
  `is_blacklist` parameter, and `UrlFilterRule("*.x.com", is_blacklist=False)`
  raises `TypeError`. Pins the corrected contract against the actual class,
  not the docstring.
- **Membership-decides pin (guard path):** append a rule directly to
  `filter._blacklist` (bypassing `add_whitelist`) and assert it still blocks —
  pins that list membership, not a per-rule flag, is the routing key.
- **Returned-values-unchanged pin:** the existing `is_allowed` /
  `get_matching_rule` value assertions (whitelist precedence, blacklist
  blocking, first-in-insertion-order) stay green against the same rule set —
  pins that removing the dead field did not change any returned value.

## Docs (SAME PR)
`docs/url_filter.md` (new, spec) + the `url-filter.md` index entry in
docs/README.md ship in the same PR as this ticket.

## Design decision (architect, cycle 291)
**Chosen resolution: Option A — remove the dead field.** The `is_blacklist`
field (line 14) is removed from `UrlFilterRule`, and the two `is_blacklist=`
keyword arguments in `add_blacklist` (line 49) and `add_whitelist` (line 53)
are removed. `UrlFilterRule` then has exactly two fields, `pattern` and
`description`, and its constructor is `UrlFilterRule(pattern, description=...)`;
constructing it with `is_blacklist=...` raises `TypeError` (unexpected
keyword). All decision behavior (`is_allowed` / `is_blocked` / `filter_urls` /
`get_blocked_urls` / `get_matching_rule`) is **exactly as today** — it never
read the field, so no returned value changes; only the dead public surface
goes. Block/allow is decided by **list membership** (whitelist list vs
blacklist list), not by a per-rule flag; the `UrlFilterRule` docstring and the
`get_matching_rule` docstring state this explicitly.

Option B (make `is_blacklist` the actual routing key via a single `_rules`
list) is **rejected**: it is a behavior change that would restructure the
two-list invariant the existing `tests/test_url_filter.py` and
`tests/deep/test_url_filter_adversarial.py` suites pin. The implementer must do
**only** Option A.

`docs/url_filter.md` (the "Contract hole (ARCH-87)" section restated as the
confirmed contract, the `UrlFilterRule` fields entry, and the
`add_blacklist`/`add_whitelist` entries) and the `url-filter.md` index line in
`docs/README.md` are reconciled in the SAME PR. Status stays **OPEN** for the
implementer.
