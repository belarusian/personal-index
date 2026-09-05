# TICKET-439: collect_system_metrics docstring over-promises CPU collection

- Status: OPEN
- Issue: #716
- File: personal_index/metrics.py
- Method: MetricsCollector.collect_system_metrics
- Symptom: docstring "Collect current system metrics" implies all SystemMetrics
  fields are gathered, but the body only sets uptime_seconds, memory_used_mb
  (guarded by resource import), and disk total/free/used (guarded by statvfs).
  cpu_percent is never assigned and stays at its dataclass default 0.0.
- Evidence: metrics.py line 19 (cpu_percent default 0.0), line 38 (to_dict only
  reads it); collect_system_metrics body (lines ~93-120) has no cpu assignment.
- Minimal additive fix: reword the docstring to enumerate exactly what is
  collected (uptime, memory_used_mb via resource when available, disk
  total/free/used via statvfs when available; cpu_percent left at default 0.0)
  and add ONE pinning test asserting the returned object's cpu_percent == 0.0
  alongside the normal collected fields.
