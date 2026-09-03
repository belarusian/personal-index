# TICKET-281: config/loader.py load_config() unguarded non-dict YAML keyed access

- Status: RESOLVED
- Issue: #390
- Module: personal_index/config/loader.py
- Class: unguarded type-assumption (yaml.safe_load -> data.get() keyed access, no guard)

## Symptom
`load_config(path)` calls `yaml.safe_load(f)` then immediately performs keyed access
(`data.get("data_dir", ...)`, `data.get("interests", [])`, etc.) with no `isinstance`
guard. Only `data is None` is handled (line 63-64). If the YAML file parses to a
non-None non-dict scalar or list (e.g. `42`, `hello`, `- a\n- b`), `data.get(...)`
raises `AttributeError` and the config load crashes instead of degrading to defaults.

## Evidence
- personal_index/config/loader.py:55  `data: dict | None = yaml.safe_load(f)`
- personal_index/config/loader.py:63  `if data is None: data = {}`   <- only None handled
- personal_index/config/loader.py:66  `data_dir=data.get("data_dir", ".personal_index")`  <- unguarded keyed access
- personal_index/config/loader.py:71  `interests=_parse_interests(data)` -> `data.get("interests", [])`  <- unguarded
- Runtime: yaml.safe_load("42") -> int, ("hello") -> str, ("- a\n- b") -> list; all raise AttributeError at .get()

## Writer type (verified)
save_config() (personal_index/config/loader.py:102) persists `yaml.dump(config.to_dict(), ...)`
where AppConfig.to_dict() (personal_index/config/models.py) returns a **dict**. Expected type = dict.

## Loader degrade contract (verified)
load_config() returns `AppConfig()` (defaults) for: missing file (line 50), YAMLError
(line 57-58), and None parse (line 63-64). The non-None non-dict case is the gap —
it should also degrade to `AppConfig()` defaults.

## Minimal additive fix
- After line 64: `if not isinstance(data, dict): return AppConfig()`
  (placed after the read/parse and before the first keyed access; matches the
  module's existing degrade-to-defaults path.)

## Regression tests (tests/test_config/test_loader.py)
- malformed: int / str / list YAML -> returns AppConfig defaults (no AttributeError)
- valid-still-works: dict YAML -> parsed fields preserved
- valid-after-invalid-not-suppressed: load invalid then valid -> valid fields preserved
