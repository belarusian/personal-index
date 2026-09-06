# TICKET-461: ContentVersioning.rollback_to docstring omits author transfer + message format

Status: OPEN
Module: personal_index/content_versioning.py
Function: ContentVersioning.rollback_to
Issue: #763

## Symptom
The docstring says "Creates a new version with the content of the specified version."
but the body actually copies BOTH `content` AND `author` from the target version,
and sets a specific `message` of `f"rollback to {version_id}"`. The docstring
omits the author transfer and the message format.

## Evidence
Line ~168-172: