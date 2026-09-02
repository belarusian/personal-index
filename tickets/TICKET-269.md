# TICKET-269: config/__init__.py non-dict JSON guard

- Status: RESOLVED
- Module: personal_index/config/__init__.py
- Class: json.load non-dict guard sweep (7th instance)

## Symptom
`AppConfig.load()` (line ~72) and `ConfigManager.load()` (line ~87) call
`data = json.load(f)` then `AppConfig.from_dict(data)`, which does
`data.get("interests", [])`. A non-dict JSON value (null / list / number)
crashes with `AttributeError: '<type>' object has no attribute 'get'`.

## Evidence (reproduced live)
- null   -> AttributeError: 'NoneType' object has no attribute 'get' (both loaders)
- [1,2,3]-> AttributeError: 'list' object has no attribute 'get' (both loaders)
- 42     -> AttributeError: 'int' object has no attribute 'get' (both loaders)

## Writer type
`AppConfig.save()` / `ConfigManager.save()` write `json.dump(config.to_dict(), ...)`
-> a **dict**. Guard expected type = dict.

## Minimal additive fix
Immediately after each `json.load`, add:
    if not isinstance(data, dict):
        return cls()          # AppConfig.load
    if not isinstance(data, dict):
        return AppConfig()    # ConfigManager.load
Safe default is a default `AppConfig()` (both loaders return an AppConfig,
not a store object with state fields).

## Tests
3 regression tests (null / list / number) per loader, mirroring the
established pattern.

## Issue: #367 (closed)

## Resolution
- Branch build24/config-json-guard, PR #368, squash-merged d93f6ea to main, CI green (3 jobs), gh #367 closed.
- 6 regression tests added (null/list/number per loader).
