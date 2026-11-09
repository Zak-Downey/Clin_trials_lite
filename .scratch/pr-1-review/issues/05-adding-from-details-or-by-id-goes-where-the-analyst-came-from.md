# 05: Adding from trial details or by NCT ID goes to the watchlist the analyst came from, and a failed add is not a success

**Blocked by:** 01, 02

**Status:** ready-for-agent

**Touches:** webapp/static/views/registry_trial.js, webapp/static/views/add_by_id.js, webapp/static/views/find.js, webapp/static/views/new_matches.js

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F8, F9. Root: User Stories 65, 70, 71, 78; Design coverage 6/4, 11/2.

**What to build:** Trial details (`#/registry/<id>`) preset Add to to the watchlist the analyst came from: Find trials' current destination, or the watchlist whose New matches linked it. Its Back link returns there. A failed add from Add by NCT ID or from trial details is an error beside the control, never in the success banner, and the typed ID is kept and focused.

- [x] Walk: from Find trials with destination "Elsewhere" (two watchlists, the first being "Myeloma"), View details shows Add to "Elsewhere", and Add to watchlist adds to "Elsewhere" — walk: test_walk_view_details_from_find_trials_presets_add_to_the_find_destination_and_adds_there; red: .scratch/pr-1-review/red/05-walks-0a2ca89.txt
- [x] Walk: from a New matches card's title, trial details preset Add to that watchlist, and Back returns to its New matches tab — walk: test_walk_view_details_from_a_new_matches_card_presets_that_watchlist_and_back_returns_to_its_tab; red: .scratch/pr-1-review/red/05-walks-0a2ca89.txt
- [x] Walk: in Add by NCT ID, a registry failure on Add after a good lookup shows an error (not `.banner`), keeps the NCT ID in the field and focuses it, with no "Open <watchlist>" link — walk: test_walk_a_registry_failure_on_add_by_nct_id_is_an_error_beside_the_field_and_keeps_and_focuses_the_id; red: .scratch/pr-1-review/red/05-walks-0a2ca89.txt
- [x] Walk: on trial details, a registry failure on Add shows an error with no link to a trial page — walk: test_walk_a_registry_failure_on_add_from_trial_details_is_an_error_with_no_link_to_a_trial_page; red: .scratch/pr-1-review/red/05-walks-0a2ca89.txt

## Comments
