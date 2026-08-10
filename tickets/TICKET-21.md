# TICKET-21: Four duplicate `Interest` dataclasses across the codebase

## Title
Four different `Interest` dataclasses exist with incompatible schemas

## Evidence
Four distinct `Interest` classes are defined:

1. **`personal_index/models.py:19`** — Has `interest_type: InterestType`, `value: str`, `created_at: str`, `enabled: bool`
2. **`personal_index/interests.py:13`** — Has `name`, `keywords`, `topics`, `url_patterns`, `priority`, `enabled` — no `interest_type` or `created_at`
3. **`personal_index/config/__init__.py:11`** — Has `topic: str`, `name: str`, `keywords`, `url_patterns`, `priority`, `enabled` — has `topic` field others lack
4. **`personal_index/config/models.py:19`** — Has `name`, `keywords`, `url_patterns`, `match_mode: MatchMode`, `priority`, `enabled` — has `match_mode` others lack

Import usage:
- `models.py` Interest: imported by `storage.py`, `interest_store.py`
- `interests.py` Interest: imported by `formatter.py`
- `config/__init__.py` Interest: not directly imported by other modules
- `config/models.py` Interest: imported by `filter/matcher.py`, `filter/engine.py`

## Impact
- Data cannot be shared between modules without conversion
- Serialization/deserialization is fragile — fields silently dropped
- `interest_store.py` creates `Interest` with `created_at=datetime.utcnow()` but `models.py:Interest.created_at` expects `str` (mypy error at line 64)

## Suggestion
1. Keep a single `Interest` in `personal_index/models.py` as the canonical model
2. Remove duplicates from `interests.py`, `config/__init__.py`, `config/models.py`
3. Update all import sites to use `personal_index.models.Interest`
4. Merge missing fields (`match_mode`, `topic`) into the canonical model
