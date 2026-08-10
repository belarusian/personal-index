# TICKET-34: Broken call — `scheduler.py` passes `interest_store` kwarg to `Crawler()` which doesn't accept it

## Title
`Crawler.__init__()` doesn't accept `interest_store` as a keyword argument, but `scheduler.py` passes it

## Evidence
In `personal_index/scheduler.py:234-236`:
