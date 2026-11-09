# 05: Adding from trial details or by NCT ID goes to the watchlist the analyst came from, and a failed add is not a success

**Blocked by:** 01, 02

**Status:** ready-for-agent

**Touches:** webapp/static/views/registry_trial.js, webapp/static/views/add_by_id.js, webapp/static/views/find.js, webapp/static/views/new_matches.js

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F8, F9. Root: User Stories 65, 70, 71, 78; Design coverage 6/4, 11/2.

**What to build:** Trial details (`#/registry/<id>`) preset Add to to the watchlist the analyst came from: Find trials' current destination, or the watchlist whose New matches linked it. Its Back link returns there. A failed add from Add by NCT ID or from trial details is an error beside the control, never in the success banner, and the typed ID is kept and focused.

- [ ] Walk: from Find trials with destination "Elsewhere" (two watchlists, the first being "Myeloma"), View details shows Add to "Elsewhere", and Add to watchlist adds to "Elsewhere"
- [ ] Walk: from a New matches card's title, trial details preset Add to that watchlist, and Back returns to its New matches tab
- [ ] Walk: in Add by NCT ID, a registry failure on Add after a good lookup shows an error (not `.banner`), keeps the NCT ID in the field and focuses it, with no "Open <watchlist>" link
- [ ] Walk: on trial details, a registry failure on Add shows an error with no link to a trial page

## Comments
