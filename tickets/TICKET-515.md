# TICKET-515: cli.py _watch_once placeholder docstring omits file/dir branch, per-file indexing, error handling

- File: personal_index/cli.py
- Function: `_watch_once` (L1436)
- Symptom: class-(b) docstring over-promise / under-description. The one-liner
  `"""Process paths in once mode — collect and index all files."""` omits the
  file-vs-dir branch, the per-file indexing, and the error handling.
- Evidence (body, L1436-1449):
    for path in paths:
        if os.path.isfile(path):
            click.echo(f"  Importing: {path}")
            files = _collect_files(path, False)
        elif os.path.isdir(path):
            files = _collect_files(path, True)
        else:
            continue
        for fp in files:
            try:
                _index_file_once(fp, data_dir)
            except Exception as e:
                click.echo(f"  ✗ Error: {e}", err=True)
  - file -> _collect_files(path, False); dir -> _collect_files(path, True);
    anything else -> skipped (continue).
  - each collected file is indexed via _index_file_once(fp, data_dir).
  - a per-file exception is caught and echoed to stderr; the loop continues.
- Minimal additive fix: reword the docstring to state the exact branch +
  per-file indexing + error handling; add ONE pinning test that witnesses the
  claim (normal file + dir indexed, guard-path non-existent path skipped,
  error path caught+echoed).
- Line-shift guard: no test pins cli.py by line number (grep of tests/ for
  lineno/getsource/_method_line_span on cli returned nothing) -> adding lines is safe.
- Issue: #889
- Status: RESOLVED (merged via PR #890, issue #889 closed)
