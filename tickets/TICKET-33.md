# TICKET-33: Missing attribute — `SystemMetrics` lacks `disk_free_mb` field

## Title
`SystemMetrics` dataclass is missing `disk_free_mb` attribute, causing runtime `AttributeError`

## Evidence
In `personal_index/metrics.py:14-28`, the `SystemMetrics` dataclass defines:
