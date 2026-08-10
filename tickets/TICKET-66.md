# TICKET-66: Unused unpacked variable `algorithm` in passwords.py (RUF059)

## Title
Unpacked variable `algorithm` is never used in `personal_index/auth/passwords.py`

## Evidence
ruff RUF059 flags 1 location:

1. `personal_index/auth/passwords.py:77` — `algorithm, iterations_str, salt, stored_hash = parts`

The `algorithm` variable is unpacked from the hash string parts but never used. The function always uses the hardcoded `"sha256"` algorithm in `_hash_with_salt()` regardless of what algorithm was used to create the hash.
