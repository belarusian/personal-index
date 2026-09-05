# TICKET-432: content_monitor.monitor.ContentMonitor.generate_health_report doc-drift (class b)

- File: personal_index/content_monitor/monitor.py
- Function: ContentMonitor.generate_health_report (lines 164-200)
- Symptom: blanket one-line docstring ("Generate a comprehensive health report.")
  that does not enumerate the guard path, the three sub-checks it runs, how the
  score is clamped, how overall_status is derived, or the returned HealthReport
  fields.
- Evidence:
  - docstring line 165: only "Generate a comprehensive health report." - no
    enumeration of the no_data guard, the disk/error/staleness checks, the score
    clamp, or the status derivation.
  - body lines 166-200: computes has_source_data / has_error_data / has_disk_data;
    returns HealthReport(overall_status="no_data", score=1.0) when all three are
    false; else runs _check_disk (critical -0.3 when total_mb > max_disk_mb,
    warning -0.1 when > 0.8*max_disk_mb), _check_errors (critical -0.3 when
    error_rate >= 5*max_error_rate, warning -0.1 when > max_error_rate),
    _check_staleness (critical -0.3 when stale_ratio > 0.5 and >1 stale, warning
    -0.1 when any stale); score = max(0.0, min(1.0, score)); overall_status via
    _determine_overall_status (critical if any critical, degraded if any warning,
    else healthy); returns HealthReport(overall_status, warnings, critical_issues,
    score, disk_usage, source_freshness=dict(...), error_rates).
- Minimal additive fix: reword the docstring to state the no_data guard (all of
  source_freshness empty, error_rates.total_crawls == 0, index_dir missing/None
  -> HealthReport(overall_status="no_data", score=1.0)), the three checks in
  order with their exact thresholds and score penalties, the score clamp to
  [0.0, 1.0], the overall_status derivation, and the returned HealthReport
  fields. Add ONE pinning test asserting the returned HealthReport fields for
  the normal case (healthy -> overall_status "healthy", score 1.0, empty
  warnings/critical, disk_usage set, source_freshness/error_rates populated) AND
  the guard path (no data -> overall_status "no_data", score 1.0, disk_usage
  None, source_freshness {}, error_rates None).
- Status: RESOLVED
- Issue: #702
