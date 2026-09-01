# TICKET-244: mypy gate RED on main - 35 errors in 7 test files

## File
tests/ (gate command `mypy . --ignore-missing-imports` exits non-zero).

## Symptom
`mypy . --ignore-missing-imports` reports 35 errors, so the local gate is RED on main.

## Evidence (measured, cycle 1)
- 14x arg-type + 3x union-attr - tests/test_interest_store.py: Interest(name,type,value,INT)
  passes an int where `keywords: list` is declared. models.py Interest.__post_init__
  DOCUMENTS this coercion (int -> priority, keywords=[]). So the int is a documented
  design constraint, NOT a defect to change in the model. Fix is test-side: pass
  priority as keyword arg (preserves the tested behavior) and guard the 3
  `store.get(...).priority` union-attr sites.
- 9x arg-type - tests/test_content_monitor.py: ContentMonitor(index_dir=str) where
  signature is `Path | None`. monitor.py:40-41 coerces str->Path at runtime, so str is
  safe; fix is test-side: wrap in Path().
- 5x operator - tests/test_url_utils.py: `in`/`not in` on `str | None` (normalize_url
  returns str|None). Fix is test-side: assert result is not None first.
- 1x assignment - tests/test_serializer.py:20: `timestamp: datetime = None`.
- 1x var-annotated - tests/test_imports.py:22: SKIP_MODULES = {} needs annotation.
- 1x var-annotated - tests/test_content_validator.py:114: item = {} needs annotation.
- 1x union-attr - tests/test_content_router.py:59: route.name on Route|None.

## Minimal additive fix
Test-side only (no model/production signature changes): keyword-arg priority + None
guards in interest_store; Path() wrap in content_monitor; `assert result is not None`
in url_utils; type annotations in serializer/imports/validator; None guard in router.

## Issue: #322 (gh)

## Status: IN PROGRESS (cycle 1)
