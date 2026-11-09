# 02: A finished check keeps the tab as the analyst left it

**Blocked by:** 01

**Status:** ready-for-agent

**Touches:** webapp/static/app.js, webapp/static/views/summary.js, webapp/static/views/new_matches.js

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F3. Root: User Stories 8, 78, 84; Design coverage 2/F, 10/2.

**What to build:** When a check finishes, the tab redraws its counts without dropping what the analyst set on it. The refresh path reads the period from the address as it now stands. Summary's period and typed custom dates, and New matches' selection, sub-view (View dismissed) and pending Dismiss confirmation, are kept per watchlist at module level, as `all_trials.js` keeps its filter and sort.

- [ ] Walk: on Summary with This month pressed, a check that finishes keeps This month pressed, the month's heading and counts, and `?period=month` in the address
- [ ] Walk: on Summary with Custom dates open and a From date typed, a check that finishes keeps the field open with the typed date
- [ ] Walk: on New matches with one match ticked, a check that finishes keeps the tick and the action bar with its count
- [ ] Walk: a pending "Yes, dismiss N" confirmation and an open View dismissed list each survive a finished check
- [ ] Walk: the All trials walk for a filter kept across a check still passes (no regression of E-004) (the walks check)

## Comments
