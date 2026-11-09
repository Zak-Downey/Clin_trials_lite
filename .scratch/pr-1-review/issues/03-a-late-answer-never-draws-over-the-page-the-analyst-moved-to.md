# 03: A late answer never draws over the page the analyst moved to, and the sidebar keeps its mark

**Blocked by:** 01, 02

**Status:** ready-for-agent

**Touches:** webapp/static/app.js, webapp/static/views/trial.js, webapp/static/views/needs_review.js, webapp/static/views/all_trials.js, webapp/static/views/summary.js

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F4, F5. Root: User Stories 3, 6, 36; Design coverage 1/1.

**What to build:** `route()` hands every render the `alive` it already gives Find trials and Registry details; the trial page, Needs review, All trials and Summary return before drawing when the analyst has moved on, and so does the sidebar. The sidebar redraw on `reviewchange` keeps the watchlist the address names marked as current.

- [ ] Walk: with the trial's answer delayed, opening a trial and then another watchlist leaves the other watchlist's page drawn, matching the address
- [ ] Walk: the same holds for Needs review, All trials and Summary: a delayed answer for a tab already left does not replace the page the address names
- [ ] Walk: after Rename from the header menu, the open watchlist keeps `aria-current="page"` and its highlight in the sidebar
- [ ] Walk: after + New watchlist, Remove from this list and its Undo, the open watchlist keeps `aria-current="page"` in the sidebar

## Comments
