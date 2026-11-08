# 11: New matches: add, dismiss, restore

**Blocked by:** 03, 10

**Status:** ready-for-agent

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 24, 77–82; Implementation Decisions › Domain changes ("Restore a dismissed match", "New matches are capped at 100"), › API (New matches); Design coverage 9/*, 11/F.

**What to build:** The New matches tab: the saved search's results not yet monitored, described as such, with checkboxes, View details links and an action bar with "Add N to watchlist" and "Dismiss N". Adding takes baselines and says "N added" with a link to All trials. Dismissing states first that the trials will not be suggested again for this watchlist, then offers Undo. View dismissed lists them with Restore. The saved search runs on every check, even with no trials; a watchlist with a saved search and no trials offers "Check for new matches".

- [ ] Walk: New matches is its own tab with a count; the list is headed "N new matches" and "Not monitored yet. Select the trials you want to add.", and nowhere calls them new registrations or changes (design 9/1)
- [ ] Walk: after the stand-in's register switch, a check for updates adds the new study to New matches, and the Needs review queue is unaffected (design 1/5)
- [ ] Walk: selecting matches shows an action bar with "N selected", "Dismiss N" and "Add N to watchlist" that never covers the last match; adding shows "N added" with a link to All trials, and the trials take baselines (design 9/3)
- [ ] Walk: Dismiss states "These trials will not be suggested again for this list" before committing, then offers Undo (design 9/4)
- [ ] Test: a dismissed match is not offered again to that watchlist by later checks unless restored, and dismissing changes nothing in any other watchlist (design 9/2, 9/4)
- [ ] Walk: "View dismissed" lists the dismissed matches with Restore; a restored match returns to New matches (design 9/2)
- [ ] Test: a check runs the saved search for a watchlist with zero trials, and reports its failure separately from the trial checks (design 9/F)
- [ ] Walk: a watchlist with a saved search and no trials offers "Check for new matches" (design 11/F)
- [ ] Walk: when the saved search found more than 100, the New matches tab and the check result say so

## Comments
