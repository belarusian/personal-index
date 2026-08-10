# TICKET-65: print() statement in production code (T201)

## Title
`print()` found in `personal_index/notifications.py` — should use logging instead

## Evidence
ruff T201 flags 1 location:

1. `personal_index/notifications.py:117` — `print(f"  {label} {notification.title}: {notification.message}")`
