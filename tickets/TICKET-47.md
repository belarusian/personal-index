# TICKET-47: Unfiltered tar.extractall() — backup.py:161

## Title
tar.extractall() without filter argument is deprecated in Python 3.12+ and will be restricted in Python 3.14

## Evidence
In personal_index/backup.py:158-161:

    with tarfile.open(str(archive_path), mode) as tar:
        members = tar.getnames()
        restored_files = len(members)
        tar.extractall(path=str(target))

The deprecation warning is triggered during test runs:

    tests/test_backup.py::TestBackupManager::test_restore_backup
      /Users/av4nda/Research/autonomous-project/personal_index/backup.py:161: DeprecationWarning: Python 3.14 will, by default, filter extracted tar archives and reject files or modify their metadata. Use the filter argument to control this behavior.
        tar.extractall(path=str(target))

## Impact
- Deprecation warning in test output
- In Python 3.14+, tar.extractall() will reject files by default, potentially breaking backup restore functionality
- Security risk: unfiltered tar extraction can lead to path traversal attacks (e.g., files with ../ in names)

## Suggestion
Add the filter argument to tar.extractall() to explicitly control extraction behavior:

    tar.extractall(path=str(target), filter="data")

The "data" filter strips metadata and prevents path traversal. For full compatibility, consider:

    if sys.version_info >= (3, 12):
        tar.extractall(path=str(target), filter="data")
    else:
        tar.extractall(path=str(target))
