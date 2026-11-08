# 10: Saved search: watch a search, replace it, manage it

**Blocked by:** 09

**Status:** ready-for-agent

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 72–76; Implementation Decisions › API (Saved search); Design coverage 1/5, 8/1, 8/2, 13/F.

**What to build:** "Watch this search" on the results opens a dialog that saves the submitted query to a chosen watchlist, with nothing selected required and no results added. If the watchlist already has a saved search, the dialog shows it and the button reads "Replace saved search". Success names the watchlist with Open watchlist. A watchlist with a saved search shows the "Saved search is on" banner with Manage, which shows the query with Edit search (Find trials pre-filled; replaces only when saved) and Turn off (keeps the trials).

- [ ] Walk: "Watch this search" opens a dialog showing the submitted query and a watchlist picker, works with no result selected, and adds no trials (design 6/2, 8/1)
- [ ] Walk: a watchlist with no trials can be the target (design 8/1)
- [ ] Walk: when the chosen watchlist already has a saved search, the dialog shows "This watchlist already has a saved search" with its current query, the button reads "Replace saved search", and Cancel leaves the old one in place (design 8/2)
- [ ] Walk: saving shows "Search saved", that the watchlist will check for new matches when you run Check for updates, and "Open watchlist" (design 8/4)
- [ ] Walk: a watchlist with a saved search shows "Saved search is on", that it runs when you check for updates and new matches need your approval, and Manage; it sits above the tabs and does not push the Needs review list down (design 1/5)
- [ ] Walk: Manage shows the query, "Edit search" and "Turn off"; Edit search opens Find trials pre-filled and replaces the saved query only when saved; Turn off removes the banner and keeps every trial (design 13/F)

## Comments
