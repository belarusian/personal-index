# TICKET-541: Add CacheStats.hit_rate / miss_rate / reset exact-contract docstrings + pinning test

Status: RESOLVED
Module: personal_index/content_cache/cache_stats.py
Methods: CacheStats.hit_rate (property), CacheStats.miss_rate (property), CacheStats.reset

## Symptom
The three public members of CacheStats carry terse docstrings that omit the exact
contract the code actually delivers. hit_rate and miss_rate say only "float between
0.0 and 1.0" and do not state: (1) the zero-total guard (when hits + misses == 0 the
property returns 0.0, not a ZeroDivisionError), (2) the exact formula (hits / (hits +
misses) for hit_rate, misses / (hits + misses) for miss_rate), (3) the rounding to 10
decimal places (round(x, 10)), and (4) that hit_rate + miss_rate == 1.0 whenever the
total is non-zero. reset says only "Reset all statistics" and does not enumerate the
five fields it zeroes (hits, misses, sets, evictions, current_size).

## Evidence (verified live)
- CacheStats().hit_rate == 0.0 and CacheStats().miss_rate == 0.0 (zero-total guard, no exception)
- CacheStats(hits=1, misses=3).hit_rate == 0.25
- CacheStats(hits=1, misses=2).hit_rate == 0.3333333333 and .miss_rate == 0.6666666667 (round to 10 dp)
- CacheStats(hits=2, misses=3).hit_rate == 0.4
- CacheStats(hits=1, misses=2).hit_rate + .miss_rate == 1.0
- reset() zeroes all five fields (hits, misses, sets, evictions, current_size)

Existing tests (tests/test_cache_stats.py) pin the day-level values (0.0, 1.0, 0.5, 0.8,
0.2) and the sum-to-1.0 invariant, but do NOT pin the exact 10-decimal rounding, the
zero-total guard as a distinct contract, or the docstring contract phrases. No reword
commit exists in git history for cache_stats.py (git log shows only the original
"feat: add content_cache module" commit) -- a fresh type-a case, not a doc-drift recovery.

## Minimal additive fix
Reword the hit_rate / miss_rate / reset docstrings to state the exact contract (zero-total
guard -> 0.0, the formula, round(..., 10), the 0.0..1.0 range, the sum-to-1.0 invariant,
and the five reset fields). Add a pinning test class asserting the key contract phrases
appear in the docstrings AND re-pinning the non-obvious behaviors (zero-total guard, the
10-decimal rounding on a non-terminating fraction, the sum-to-1.0 invariant, and the
five-field reset).

Issue: #957
