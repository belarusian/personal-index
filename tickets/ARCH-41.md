# ARCH-41: tags — create_tag silently overwrites metadata and resets created_at on a name collision

Status: OPEN
Component: `personal_index/tags.py`
Issue: #1116
Refs: ARCH-2 (#983 umbrella)

## Symptom

`TagStore.create_tag` (lines 97-103) is documented as "Create a tag, or
replace an existing tag with the same name," but on a name collision the body
silently does three things the contract never states: