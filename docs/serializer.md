# serializer — `personal_index.serializer`

> Module identity: `personal_index/serializer.py` (top-level module, 131 lines).
> Not to be confused with any `content_*` serializer — there is no
> `personal_index.content_serializer`; this is the only `serializer` in the
> package (verified: `ls personal_index/ | grep -i serial` → `serializer.py`
> only). Live production module: `tests/test_serializer.py` +
> `tests/deep/test_serializer_adversarial.py` import
> `from personal_index.serializer import ...`.

Data serialization utilities for indexed content. Converts between Python
objects and JSON / CSV / dict representations, with a configurable
`SerializationConfig` and a `default` handler for types `json` cannot encode
natively (datetime, dataclass, arbitrary objects).

## Public API

### Exceptions
- `SerializationError(Exception)` — raised when serialization fails
  (`to_json` wraps `TypeError`/`ValueError`; `to_dict` raises it for a type
  that is neither a dataclass, an object with `__dict__`, nor a dict).
- `DeserializationError(Exception)` — raised when deserialization fails
  (`from_json` wraps `json.JSONDecodeError`; `from_csv` raises it when a
  headerless CSV is given without `fieldnames` — see Contract Hole 1).

### `SerializationConfig` (dataclass)
Fields (all honored by `Serializer`):
- `indent: int = 2` — JSON indentation passed to `json.dumps`.
- `ensure_ascii: bool = False` — JSON `ensure_ascii` flag.
- `default_handler: bool = True` — when `True`, `to_json` passes
  `_default_handler` as `json.dumps(default=...)`; when `False`, no `default`
  is passed and non-JSON types raise `SerializationError`.
- `include_none: bool = True` — when `False`, `_dataclass_to_dict` omits
  fields whose value is `None`.

### `Serializer`
- `__init__(config: SerializationConfig | None = None)` — stores
  `config or SerializationConfig()`.
- `to_json(data: Any) -> str` — `json.dumps(self._prepare(data), indent,
  ensure_ascii, default=_default_handler if config.default_handler else None)`.
  `_prepare` recursively converts dataclasses/dicts/lists; scalars pass
  through. Wraps `TypeError`/`ValueError` in `SerializationError`.
- `from_json(json_str: str) -> Any` — `json.loads(json_str)`; returns whatever
  the document actually contains (dict, list, str, int, float, bool, or None)
  — **not necessarily a mapping**; callers requiring a dict must
  `isinstance(result, dict)`. Wraps `json.JSONDecodeError` in
  `DeserializationError`.
- `to_csv(data: list[dict], include_header: bool = True) -> str` —
  `csv.DictWriter` over `data[0].keys()` as fieldnames, `extrasaction="ignore"`.
  Returns `""` for empty `data`. `include_header=False` omits the header row.
  Each cell is stringified via `_prepare_row` (non-str → `str(v)`).
- `from_csv(csv_str: str) -> list[dict]` — `csv.DictReader` over the string;
  returns `[]` for empty/whitespace input. **The first line is always treated
  as the header** (see Contract Hole 1).
- `to_dict(obj: Any) -> dict` — dataclass → `_dataclass_to_dict`; object with
  `__dict__` → `obj.__dict__`; dict → itself; otherwise raises
  `SerializationError`.
- `_dataclass_to_dict(obj) -> dict` (private, contract-relevant) — iterates
  `fields(obj)`; omits `None` values when `config.include_none` is `False`;
  recurses into nested dataclasses and into dataclass members of lists.
- `_prepare(data) -> Any` (private, contract-relevant) — recursive: dataclass →
  `_dataclass_to_dict`; dict → `{k: _prepare(v)}`; list → `[_prepare(item)]`;
  scalar → itself.
- `_prepare_row(data: dict) -> dict` (private, contract-relevant) — `{k: str(v)
  if not isinstance(v, str) else v}`.
- `_default_handler(obj) -> Any` (private, contract-relevant) — `datetime` →
  `isoformat()`; dataclass → `_dataclass_to_dict`; object with `__dict__` →
  `obj.__dict__`; otherwise `str(obj)`.

## Contract Hole 1 — `to_csv(include_header=False)` → `from_csv` round-trip silently corrupts the data (ARCH-74)

`to_csv` exposes `include_header: bool = True` so a caller can emit a
headerless CSV. But `from_csv` has no matching parameter: it always uses
`csv.DictReader` with the **first line as the header**. So a headerless CSV
produced by `to_csv(data, include_header=False)` is mis-read on the way back:
the first data row is consumed as the header and the remaining rows are
mapped onto it.

Verified (this cycle):

    data = [{'name':'Alice','age':'30'},{'name':'Bob','age':'25'}]
    s.to_csv(data, include_header=False)
      -> 'Alice,30\r\nBob,25\r\n'
    s.from_csv(that)
      -> [{'Alice': 'Bob', '30': '25'}]      # column names lost, values mis-mapped

The real column names (`name`, `age`) are gone and the values are re-keyed by
the first row's values — a **silent data-corruption** on a first-class public
path (no exception, no warning). The `include_header=False` parameter exists
precisely to omit the header, but the round-trip partner cannot honor that
omission: there is no way to tell `from_csv` "the first line is data, not a
header."

### Recommended contract
`from_csv(csv_str: str, include_header: bool = True,
fieldnames: list[str] | None = None) -> list[dict]`:
- `include_header=True` (default): **unchanged** — first line is the header;
  `fieldnames` is ignored (backward compatible).
- `include_header=False`: `fieldnames` is **required**. If `fieldnames is
  None`, raise `DeserializationError` (column names cannot be inferred from
  headerless data). Otherwise use
  `csv.DictReader(io.StringIO(csv_str), fieldnames=fieldnames)`.
- Empty/whitespace input still returns `[]` (existing guard preserved).

The docstring must state this exact conditional (the first line is the header
unless `include_header=False`, in which case `fieldnames` is required) rather
than the current blanket "Deserialize CSV string to list of dicts."

## Secondary notes (verified clean this cycle — do not re-ticket)
- CSV special-character round-trip is **safe**: a value containing a comma,
  quote, or newline is quoted by `csv.DictWriter` and re-parsed exactly by
  `csv.DictReader` (verified: `{'a':'x,y','b':'q"z','c':'n\nl'}` round-trips
  losslessly).
- `to_json` / `from_json` error contract is **consistent**: `to_json` wraps
  `TypeError`/`ValueError` in `SerializationError`; `from_json` wraps
  `json.JSONDecodeError` in `DeserializationError`. No raw exception leaks.
- `_dataclass_to_dict` / `_prepare` **recurse** into nested dataclasses and
  into dataclass members of lists (not one-level-only).
- `SerializationConfig` is **not dead config**: all four fields
  (`indent`, `ensure_ascii`, `default_handler`, `include_none`) are read by
  `Serializer` (`to_json` reads the first three; `_dataclass_to_dict` reads
  `include_none`).
