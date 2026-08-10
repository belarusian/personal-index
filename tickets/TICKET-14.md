# TICKET-14: Duplicate HealthCheckResult and HealthReport classes with divergent schemas

## Title
`HealthCheckResult` and `HealthReport` are defined in both `content_health.py` and `health_report.py` with different field names and behavior

## Evidence
Two modules define the same class names with incompatible schemas:

### `personal_index/content_health.py` (lines 32-89)
