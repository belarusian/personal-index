# TICKET-391: _parse_directive placeholder docstring (class-(b) doc-drift)

**File:** personal_index/robots_parser.py
**Line:** 83
**Symptom:** Docstring `"""Handle one line's directive parsing."""` is a
placeholder that does not state the actual behavior: it does not describe
that the function splits the line on the first ":", lowercases/strips the
key, and returns a `(current_agent, current_rules)` tuple (where
`current_agent` is the agent string or None, and `current_rules` is the
accumulated rule list for the current agent). It also does not mention the
side effects on `policy` (extending rules on agent switch, setting
crawl_delay, appending sitemap_urls).

**Evidence:** Line 83: `"""Handle one line's directive parsing."""`
The body (lines 84-101) performs: `line.split(":", 1)`, `key.lower().strip()`,
conditional dispatch on key_lower, and `return current_agent, current_rules`.

**Minimal additive fix:** Reword the docstring to state the exact behavior
(split on first ":", strip/lowercase key, return (agent_or_None, rules);
side effects on policy). Add ONE pinning behavior test that witnesses the
returned tuple for a directive line (Disallow) and a comment/blank line
(returning None agent).

**Status:** OPEN
**Issue:** #620
