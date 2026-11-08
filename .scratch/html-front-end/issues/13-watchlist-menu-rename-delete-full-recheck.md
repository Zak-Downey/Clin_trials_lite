# 13: Watchlist menu: rename, delete and full recheck

**Blocked by:** 03, 05, 09

**Status:** needs-triage

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 93–96; Implementation Decisions › Domain changes ("Retention"); Design coverage 12/F, 13/1–13/4.

**What to build:** The watchlist's ⋯ menu with Rename watchlist, Manage saved search (ticket 10's dialog), Full recheck and Delete watchlist, each opening its own dialog. Rename checks names inline. Full recheck explains that it ignores the registry's update date and finishes with its own label. Delete names the watchlist, states exactly what goes and what stays, keeps history, and cannot be undone.

- [ ] Walk: the ⋯ menu offers Rename watchlist, Manage saved search, Full recheck and Delete watchlist, and each opens its own dialog; no form both creates and renames or deletes (design 13/1)
- [ ] Walk: Rename shows the current name, refuses an empty or duplicate name inline, and Save or Cancel returns to the same view and scroll position (design 13/2)
- [ ] Walk: Full recheck explains that it compares every monitored field even when the registry's update date has not moved, runs once, and finishes with its own completion label; normal checks are unaffected (design 13/4, 12/F)
- [ ] Test: a normal check skips a trial whose registry update date has not moved, and a full recheck compares it anyway (design 12/F)
- [ ] Walk: Delete watchlist names it and says it removes the watchlist, its saved search and its memberships, that trials in other watchlists are unchanged, that history is kept while trials no longer in any watchlist stop being checked, and that it cannot be undone (design 13/3)
- [ ] Test: deleting a watchlist keeps every trial's snapshots and changes, and trials still in another watchlist keep being checked (design 13/3)

## Comments
