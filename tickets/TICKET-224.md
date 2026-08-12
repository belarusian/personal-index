# TICKET-224: Duplicate versioning functionality

## Evidence
- `personal_index/versioning.py`: ContentVersion with url/version_id/content_hash/title
- `personal_index/content_versioning.py`: ContentVersion with version_id/content/created_at/author/message
- Both track content versions but with different field sets

## Impact
- Two incompatible ContentVersion dataclasses
- Unclear which module to use for versioning needs

## Suggestion
Consolidate into a single versioning module with a unified ContentVersion model.
