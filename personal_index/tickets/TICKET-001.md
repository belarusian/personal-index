# TICKET-001: test_content_monitor.py imports non-existent symbols

**File:** `tests/test_content_monitor.py:13-19`

**What's wrong:**
The test file imports `DiskUsageInfo`, `ErrorRateInfo`, `HealthReport`, and `SourceFreshness` from `personal_index.content_monitor`, but none of these classes exist in that module. The `content_monitor/__init__.py` only exports `Alert`, `AlertManager`, `ContentMonitor`, and `HealthChecker`.

**Evidence:**
