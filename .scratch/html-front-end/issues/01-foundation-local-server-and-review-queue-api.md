# 01: Foundation: the local server, its API seam and the Needs review queue

**Blocked by:** None (can start immediately)

**Status:** needs-triage

**Touches:** *

**Kind:** foundational

**Spec sections (read these, not this ticket's paraphrase):** Solution; Implementation Decisions › Shape, › Domain changes ("Changes carry their IDs to callers", "An existing database file is upgraded in place"), › API; Testing Decisions › Seam 1; Further Notes (the foundational ticket).

**What to build:** The skeleton every other ticket builds on. One command starts a standard-library HTTP server bound to localhost and opens the browser on a static HTML page (no build step, no framework, no CDN). The page shell has the two top-level destinations and a sidebar of watchlists with counts; a watchlist opens on a read-only Needs review queue served by the JSON API. The server is made by a factory taking the database path and the registry fetch and search functions, so the API is tested in-process against a temporary database with the suite's existing stub fetchers and finders. Changes now reach callers with their IDs and check identity. Code layout set here and kept by every later ticket: a `webapp` package (server and factory, a route table, one API module per area), static files under it (shell and router, one stylesheet with colours as custom properties, one view module per screen), `run.py` at the root, API tests as `tests/test_api_*.py`.

- [ ] `python run.py` starts the server on 127.0.0.1 only, on a free port unless one is given, prints the address and opens the browser; the database is `MONITOR_DB` if set, else `monitor.db` in the start folder (Implementation Decisions › Shape)
- [ ] The server factory takes the database path and the registry fetch and search functions; an API test runs it in-process against a temporary database with the stub fetchers and finders from the test fixtures, and no test reaches the live registry
- [ ] Every API error response carries a stable `kind` and a human-readable message
- [ ] A `monitor.db` written by the current app opens with its data intact and its schema upgraded in place
- [ ] Listing a trial's changes returns each change's ID, its check (the shared detection time of one check of one trial), previous and new values, registry-updated date, detected time, review state and simulated flag
- [ ] The watchlists endpoint returns each watchlist with its trial count, the number of its trials needing review, its last-checked time and whether a saved search is on (design 1/1)
- [ ] The Needs review endpoint returns only the watchlist's trials with unreviewed changes, newest detection first, with the counts of trials and of unreviewed field changes as separate numbers (design 1/2)
- [ ] Each queue entry carries the trial heading (acronym, else brief title), NCT ID, phase, sponsor, registry status, the names of the changed fields, the detected time, its change count and whether any change is simulated (design 1/F)
- [ ] Times the API returns are in the machine's local time zone, with the zone named
- [ ] The page shell, sidebar and Needs review queue render from the API; their visible behaviour is proven by the walk in ticket 02

## Comments
