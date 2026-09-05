# TICKET-444: content_health.py ContentHealthChecker.check_item docstring over-promises (blanket)

Status: OPEN
Issue: #726
Module: personal_index/content_health.py
Method: ContentHealthChecker.check_item
Symptom: class-(b) doc-drift - blanket docstring
Evidence: line 142 `"""Check health of a single content item."""`

## Detail
The `check_item` docstring is a one-line blanket claim that does not enumerate:
- the seven checks it runs (5 always-run + 2 conditional):
  1. url: `url and len(url) > 5` (invalid_url, HIGH)
  2. title presence: `title and len(title) >= config.min_title_length` (missing_title, MEDIUM)
  3. title length: `len(title) <= config.max_title_length` (title_too_long, LOW)
  4. content length: `len(content) >= config.min_content_length` (low_content, MEDIUM)
  5. status code: `200 <= status_code < 400` (bad_status, HIGH)
  6. tags: ONLY when `config.require_tags` is set, `tags and len(tags) >= config.min_tags` (missing_tags, LOW)
  7. score: ONLY when `config.require_score` is set, `score >= config.min_score` (low_score, LOW)
- the status determination: UNHEALTHY if any issue is HIGH or CRITICAL; WARNING if any
  issue is MEDIUM or any issue at all; else HEALTHY
- the score formula: `checks_passed / checks_total * 100` (0.0 when no checks ran)
- the returned `HealthCheckResult` fields: url, title, status, issues, score,
  checks_passed, checks_total

## Minimal additive fix
Reword the docstring to state the EXACT behavior (enumerate the checks, the two
conditional checks, the status determination, the score formula, and the returned
HealthCheckResult fields). Add ONE pinning test that pins the RETURNED OBJECT fields
for both the normal case (default config: 5 checks, HEALTHY) and the guard path
(require_tags/require_score config: 7 checks, conditional checks run).
