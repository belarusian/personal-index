# Backup (`personal_index.backup`)

Status: **spec** — audited against current code (cycle 240).

`BackupManager` manages tar / tar.gz archives of a source directory plus a
per-backup JSON manifest, under a single backup directory (default
`~/.personal_index/backups`). `BackupManifest` is a `@dataclass` describing one
backup. This is a **live production module** — it has a dedicated test file
(`tests/test_backup.py`, 47 tests) and is imported by
`tests/deep/test_negslice_sweep3_adversarial.py`. It is **distinct from
`personal_index.content_backup.backup_manager`** (a different `BackupManager`
class in the `content_backup` subpackage); this page covers only
`personal_index/backup.py`.

## Public API

### `BackupManifest`

    @dataclass
    class BackupManifest:
        backup_id: str = ""
        created_at: str = ""
        source_dir: str = ""
        files: list[str] = field(default_factory=list)
        total_size: int = 0
        file_count: int = 0
        metadata: dict = field(default_factory=dict)
        def __post_init__(self) -> None
        def to_dict(self) -> dict
        @classmethod
        def from_dict(cls, data: dict) -> BackupManifest

- `__post_init__()`: stamps `created_at` (UTC ISO) when empty and generates
  `backup_id` as `{YYYYMMDD_HHMMSS}_{6-hex-uuid}` when empty. The timestamp
  prefix is what makes `list_backups()`'s filename sort chronological.
- `to_dict()`: returns a 7-key dict (`backup_id`, `created_at`, `source_dir`,
  `files`, `total_size`, `file_count`, `metadata`).
- `from_dict(data)`: `cls(**data)` — **no field validation.** A dict missing a
  key raises `KeyError`; a dict with an unexpected key raises `TypeError`.
  Callers (`list_backups`, `get_backup_info`, `restore_backup`) each catch
  these and degrade differently (see below).

### `BackupManager`

    class BackupManager:
        def __init__(self, backup_dir: str | None = None) -> None
        @staticmethod
        def _create_archive(files: list[Path], archive_path: Path, mode: str, source_path: Path) -> None
        @staticmethod
        def _save_manifest(manifest: BackupManifest, manifest_path: Path) -> None
        def create_backup(self, source_dir: str, include_patterns: list[str] | None = None, exclude_patterns: list[str] | None = None, compress: bool = True) -> BackupManifest
        def _populate_manifest(self, manifest: BackupManifest, files: list[Path], source: Path) -> None
        def _build_archive(self, manifest: BackupManifest, files: list[Path], backup_path: Path, source: Path, compress: bool) -> Path
        def list_backups(self) -> list[BackupManifest]
        def restore_backup(self, backup_id: str, target_dir: str) -> dict[str, object]
        def _find_archive(self, manifest: BackupManifest, backup_path: Path, backup_id: str) -> Path
        @staticmethod
        def _extract_archive(archive_path: Path, mode: str, target: Path) -> int
        def delete_backup(self, backup_id: str) -> bool
        def get_backup_info(self, backup_id: str) -> BackupManifest | None
        def get_total_backup_size(self) -> int
        def cleanup_old_backups(self, keep: int = 5) -> list[str]
        def _collect_files(self, source: Path, include: list[str] | None = None, exclude: list[str] | None = None) -> list[Path]

- `__init__(backup_dir=None)`: `self._backup_dir = backup_dir or
  str(Path.home() / ".personal_index" / "backups")`. No directory is created
  here; `create_backup` creates it lazily.
- `_create_archive(files, archive_path, mode, source_path)` (staticmethod):
  opens `tarfile.open(archive_path, mode)` and `tar.add`s each file with an
  arcname relative to `source_path`. **Error path:** any `OSError` or
  `tarfile.TarError` (disk full, permission denied, non-writable path, archive
  path being a directory) is translated into a clean `RuntimeError`
  (`"Failed to create archive {path}: {exc}"`).
- `_save_manifest(manifest, manifest_path)` (staticmethod):
  `with open(manifest_path, "w") as f: json.dump(manifest.to_dict(), f,
  indent=2)`. **Non-atomic and unflushed** — see Secondary notes (same class as
  ARCH-71; not re-ticketed here).
- `create_backup(source_dir, include_patterns=None, exclude_patterns=None,
  compress=True)`: **guard path** — `if not Path(source_dir).exists(): raise
  FileNotFoundError`. Otherwise: `mkdir(parents=True, exist_ok=True)` the
  backup dir, `_collect_files`, `_populate_manifest`, `_build_archive`
  (`backup_{id}.tar.gz` + mode `w:gz` when `compress`, else
  `backup_{id}.tar` + mode `w`), then `_save_manifest` **twice** — once before
  and once after stamping `metadata["archive_path"]` and
  `metadata["compressed"]`. Returns the manifest.
- `_populate_manifest(manifest, files, source)`: sets `manifest.files` to the
  source-relative paths, `file_count = len(files)`, `total_size =
  sum(f.stat().st_size)`.
- `list_backups()`: **guard path** — `if not backup_path.exists(): return []`.
  Otherwise globs `backup_*.json` in **sorted filename order** (oldest-first,
  relying on the `backup_id` timestamp prefix). For each file: `json.load`,
  `if not isinstance(data, dict): continue`, else `BackupManifest.from_dict`.
  **Silent degrade:** any `json.JSONDecodeError`, `KeyError`, or `TypeError`
  is caught and the file is skipped (no raise, no log). Returns the list of
  parseable manifests.
- `restore_backup(backup_id, target_dir)`: **guard paths** — missing manifest
  file → `FileNotFoundError`; manifest JSON that fails `json.load` →
  `ValueError`; decoded value that is not a dict → `ValueError`;
  `BackupManifest.from_dict` raising `KeyError`/`TypeError` → `ValueError`.
  Then `_find_archive`, `mode = "r:gz" if archive ends with ".tar.gz" else
  "r"`, `target.mkdir(parents=True, exist_ok=True)`, and
  `_extract_archive(archive_path, mode, target)`. Returns a 4-key dict
  (`backup_id`, `target_dir`, `files_restored`, `restored_at`). **See Contract
  Hole 1** — the extract silently overwrites pre-existing files in
  `target_dir`.
- `_find_archive(manifest, backup_path, backup_id)`: prefers
  `manifest.metadata["archive_path"]` if it exists and is a file; else falls
  back to `backup_{id}.tar.gz`, then `backup_{id}.tar`. **Error path:** if
  none exists → `FileNotFoundError` (`"Archive not found for backup: {id}"`).
- `_extract_archive(archive_path, mode, target)` (staticmethod):
  `with tarfile.open(archive_path, mode) as tar: count = len(tar.getnames());
  tar.extractall(path=target, filter="data")`. **Error path:** any
  `tarfile.TarError` or `EOFError` (corrupt archive, truncated `.tar.gz`) is
  translated into a clean `ValueError` (`"Corrupt or unreadable archive
  {path}: {exc}"`). Because `len(tar.getnames())` runs **before**
  `extractall`, a corrupt/truncated archive raises **before** any file is
  written to `target` — the corrupt-archive path leaves `target` untouched.
  `filter="data"` blocks path traversal (TICKET-47).
- `delete_backup(backup_id)`: **guard path** — `if not manifest_file.exists():
  return False`. Otherwise unlinks `backup_{id}.tar.gz` and `backup_{id}.tar`
  (whichever exist), then unlinks the manifest. Returns `True`. Removes both
  the archive(s) and the manifest, so it does not leave an orphan.
- `get_backup_info(backup_id)`: **never raises.** Returns the parsed manifest,
  or `None` when the file is missing, its JSON is unparseable, the decoded
  value is not a dict, or `from_dict` raises `KeyError`/`TypeError`.
- `get_total_backup_size()`: **guard path** — `if not backup_path.exists():
  return 0`. Otherwise sums `st_size` over every `backup_*.tar*` archive
  (manifest `.json` files are ignored). Returns `0` when the dir exists but
  holds no archives.
- `cleanup_old_backups(keep=5)`: **guard path** — `if keep <= 0: return []`
  (never deletes when `keep` is non-positive). Otherwise, only when
  `len(list_backups()) > keep`, deletes the **oldest** `len - keep` backups
  (`backups[:-keep]`), keeping the `keep` newest. Returns only the IDs that
  `delete_backup` succeeded on (a strict subset is possible). Returns `[]`
  when there is nothing to delete.
- `_collect_files(source, include=None, exclude=None)`: `os.walk(source)`,
  pruning hidden dirs and `__pycache__`/`.git`/`.pytest_cache`/`.mypy_cache`/
  `*.egg-info`/`node_modules`. Skips files matching any `exclude` pattern;
  when `include` is non-empty, keeps only files matching at least one
  `include` pattern. Returns the list of `Path`s.

## Contract Holes

### Contract Hole 1 — `restore_backup` silently overwrites pre-existing files in `target_dir` (ARCH-72)

`restore_backup` (line 160) does `target.mkdir(parents=True, exist_ok=True)`
(line 189) and then `_extract_archive` (line 190) →
`tar.extractall(path=target, filter="data")` (line 226). `tarfile.extractall`
**overwrites any file in `target` whose path collides with an archive member,
with no guard, no conflict detection, and no signal.** If the caller points
`target_dir` at a directory that already holds data (a live data dir, a
previously-restored backup, or any existing tree), the colliding files are
**silently clobbered** — the pre-existing content is destroyed and the return
dict reports only `files_restored` (the count of archive members), never that
existing files were overwritten. The `restore_backup` docstring
(`"Restore a backup to the target directory."`) and the `_extract_archive`
docstring both omit this overwrite behavior entirely, so a caller reading the
contract has no reason to expect data loss.

This is the **destructive user-facing** half of the module: unlike the
corrupt-archive path (which raises `ValueError` **before** writing anything,
because `len(tar.getnames())` precedes `extractall`), the clobber happens on
the **happy path** with a valid archive and a valid manifest. It is the same
"advertised safety not actually provided" class as ARCH-39/40/41/42/44/46
(silent overwrite / silent data loss on a write path), and it is the single
most important hole in this module because it destroys caller-owned data
rather than the module's own persisted state.

## Secondary notes

- `_save_manifest` (line 86) is **non-atomic and unflushed**: `open(..., "w")`
  truncates the manifest before writing and there is no `flush()`/`fsync()`. A
  crash mid-write leaves a truncated/partial `backup_{id}.json`. The next
  `list_backups()` / `get_backup_info()` then **silently skips** that file
  (JSONDecodeError caught → `continue` / `None`), so the backup's archive
  becomes **orphaned and invisible** to `list_backups`/`cleanup_old_backups`
  (the archive is still on disk but no manifest points to it). This is the
  same durability class as ARCH-71 (`search_index._save`) and ARCH-40/44/46
  (`storage`/`content_pin`/`content_versioning` `_save`); it is **not
  re-ticketed here** — ARCH-71 is the claim-queue instance of the class and
  this note records the divergence for the docs record.
- `BackupManifest.from_dict` is `cls(**data)` with no validation, so the
  three read paths degrade **differently** on the same corrupt manifest:
  `list_backups` skips it, `get_backup_info` returns `None`, and
  `restore_backup` raises `ValueError`. That asymmetry is intentional (a
  restore must fail loudly) and is pinned by
  `tests/test_backup.py::test_restore_backup_raises_for_null_manifest` /
  `_for_list_manifest` / `_for_number_manifest`.
- `create_backup` calls `_save_manifest` **twice** (before and after stamping
  `metadata["archive_path"]`/`metadata["compressed"]`), so the on-disk
  manifest only carries `archive_path` after the second write; a crash between
  the two writes leaves a manifest without `archive_path` (restorable only via
  the `_find_archive` filename fallback).
- `delete_backup` removes **both** the archive(s) and the manifest, so it does
  not leave an orphan (the briefing's "orphaned archive" candidate is not a
  hole in the current code).
- `cleanup_old_backups` deletes the **oldest** (`backups[:-keep]`), not the
  newest, and is a no-op for `keep <= 0` — both behaviors are documented in the
  docstring and pinned; not holes.
