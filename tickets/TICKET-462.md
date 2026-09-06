# TICKET-462: RobotsPolicy.can_fetch docstring omits matching predicates

Status: RESOLVED
Issue: #765
Module: personal_index/robots_parser.py
Symptom: can_fetch() docstring is the blanket claim "Check if a URL can be
fetched according to robots.txt." The body actually applies four named
predicates: (1) case-insensitive user-agent matching, (2) specific user-agent
rules take precedence over wildcard (*) rules, (3) among applicable rules the
longest matching pattern wins (most specific), (4) if no rules apply to the
requested user agent the URL is allowed (default-allow).
Evidence: line 30 (docstring) vs lines 33-58 (body).
Fix: Reword docstring to enumerate the four predicates. Add ONE behavior test
pinning case-insensitive UA match (normal) + default-allow when no rules apply
(guard path).
