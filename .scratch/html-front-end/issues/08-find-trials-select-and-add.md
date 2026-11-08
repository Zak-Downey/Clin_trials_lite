# 08: Find trials: select results and add them to a watchlist

**Blocked by:** 05, 07

**Status:** needs-triage

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 62–68; Implementation Decisions › Domain changes ("Details of a trial that is not monitored", bulk add), › API (Membership); Design coverage 6/3, 6/4, 8/4.

**What to build:** Selecting and adding from search results. Each result row has a real checkbox and a "View details" title link; "Select 10 on this page" selects the page. Selections survive paging, viewing a trial and leaving and returning to Find trials. An action bar appears with the count, Clear, an "Add to" picker preset to the watchlist the analyst came from, and "Add N trials"; it reserves space below the results. Adding reports exactly what happened and clears the completed selection. The details of a trial not yet monitored come from one registry fetch, shown with the same sections as a monitored trial and an Add to watchlist action.

- [ ] Walk: each result has a real checkbox and a separate title link; ticking never opens, and the link never selects; long titles wrap (design 6/3)
- [ ] Walk: "Select 10 on this page" selects only the current page; selections survive paging, opening a result's details and coming back, and leaving Find trials for Watchlists and returning, with the total selected stated (design 6/3, 6/F)
- [ ] Walk: once something is selected an action bar shows "N trials selected", Clear, "Add to <watchlist>" and "Add N trials", and the last result can still be scrolled clear of it (design 6/4)
- [ ] Walk: opened from a watchlist's "Add trials", the destination is preset to that watchlist (design 6/4)
- [ ] Test: adding several trials returns which were added, which were already in the watchlist and which failed, by NCT ID
- [ ] Walk: adding shows "N added; M already in this list" with a link to the watchlist, and clears the selection that was added (design 8/4)
- [ ] Walk: a newly added trial appears in All trials with "No changes" and does not enter Needs review
- [ ] Walk: "View details" on a result not yet monitored shows its header facts and Trial details sections with no Changes or History tabs, and an "Add to watchlist" action; nothing is stored until it is added

## Comments
