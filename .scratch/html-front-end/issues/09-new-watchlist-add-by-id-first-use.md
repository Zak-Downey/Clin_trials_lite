# 09: New watchlist, Add by NCT ID, and the first-use screen

**Blocked by:** 08

**Status:** needs-triage

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 5, 66, 69–71, 91, 92, 94, 97; Implementation Decisions › Domain changes ("Look up a trial without adding it", "Distinct error kinds"); Design coverage 8/3, 8/F, 11/*.

**What to build:** Three small flows that share a destination. The New watchlist dialog, from the sidebar and from inside every destination picker, checks empty and duplicate names inline and returns the analyst to their task with the new watchlist selected. The Add by NCT ID tab looks a trial up and shows it before Add to watchlist, with distinct messages for each failure. An empty watchlist shows only "Monitor your first trial" with Find trials and Add by NCT ID, each carrying the watchlist as destination. This ticket also builds the shared dialog behaviour every later dialog uses.

- [ ] Walk: "+ New watchlist" in the sidebar and "New watchlist" inside the Add to picker each open the dialog; an empty or duplicate name is refused inline; Create returns to the task with the new watchlist selected as destination (design 8/3)
- [ ] Walk: every dialog traps focus, Escape cancels without changes and returns focus to the control that opened it, and saving or cancelling leaves the page on the same view and scroll position (design 8/F)
- [ ] Walk: Add by NCT ID names its destination; "Look up trial" shows the ID, title, sponsor and status with "Add to watchlist"; nothing is added before that button (design 11/3)
- [ ] Test: looking up a trial returns its ID, heading, official title, sponsor and status without adding it, and the four failures are distinct error kinds: invalid format, not found, already in this watchlist, registry unavailable
- [ ] Walk: each of the four failures shows its own message in place, keeps the typed ID and focuses the input; the invalid-format message explains "NCT followed by 8 digits" (design 11/4)
- [ ] Walk: an empty watchlist shows only "Monitor your first trial", the baseline explanation and "You choose when to check for updates", with no summary, activity or check controls (design 11/1)
- [ ] Walk: its "Find trials" and "Add by NCT ID" buttons open those tabs with this watchlist as destination (design 11/2)
- [ ] Walk: the first trial added to a watchlist takes its baseline and does not appear in Needs review (design 11/F)

## Comments
