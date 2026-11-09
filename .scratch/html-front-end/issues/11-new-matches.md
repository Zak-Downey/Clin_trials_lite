# 11: New matches: add, dismiss, restore

**Blocked by:** 03, 10

**Status:** done

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 24, 77–82; Implementation Decisions › Domain changes ("Restore a dismissed match", "New matches are capped at 100"), › API (New matches); Design coverage 9/*, 11/F.

**What to build:** The New matches tab: the saved search's results not yet monitored, described as such, with checkboxes, View details links and an action bar with "Add N to watchlist" and "Dismiss N". Adding takes baselines and says "N added" with a link to All trials. Dismissing states first that the trials will not be suggested again for this watchlist, then offers Undo. View dismissed lists them with Restore. The saved search runs on every check, even with no trials; a watchlist with a saved search and no trials offers "Check for new matches".

- [x] Walk: New matches is its own tab with a count; the list is headed "N new matches" and "Not monitored yet. Select the trials you want to add.", and nowhere calls them new registrations or changes (design 9/1) — walk: test_walk_new_matches_is_its_own_tab_with_a_count_and_never_called_a_change; test_walk_selecting_matches_shows_an_action_bar_that_never_covers_the_last_match_and_adding_takes_baselines (tab counts on Needs review and All trials); red: .scratch/html-front-end/red/11-walks-63dfd1f.txt
- [x] Walk: after the stand-in's register switch, a check for updates adds the new study to New matches, and the Needs review queue is unaffected (design 1/5) — walk: test_walk_after_the_register_switch_a_check_adds_the_new_study_to_new_matches_and_needs_review_is_unaffected; red: .scratch/html-front-end/red/11-walks-63dfd1f.txt
- [x] Walk: selecting matches shows an action bar with "N selected", "Dismiss N" and "Add N to watchlist" that never covers the last match; adding shows "N added" with a link to All trials, and the trials take baselines (design 9/3) — walk: test_walk_selecting_matches_shows_an_action_bar_that_never_covers_the_last_match_and_adding_takes_baselines; red: .scratch/html-front-end/red/11-walks-63dfd1f.txt
- [x] Walk: Dismiss states "These trials will not be suggested again for this list" before committing, then offers Undo (design 9/4) — walk: test_walk_dismiss_states_the_consequence_before_committing_and_then_offers_undo; red: .scratch/html-front-end/red/11-walks-63dfd1f.txt
- [x] Test: a dismissed match is not offered again to that watchlist by later checks unless restored, and dismissing changes nothing in any other watchlist (design 9/2, 9/4) — test: test_a_dismissed_match_is_not_offered_again_by_later_checks_and_nothing_else_changes; red: .scratch/html-front-end/red/11-unit-d223300.txt
- [x] Walk: "View dismissed" lists the dismissed matches with Restore; a restored match returns to New matches (design 9/2) — walk: test_walk_view_dismissed_lists_dismissed_matches_with_restore_and_a_restored_one_returns; red: .scratch/html-front-end/red/11-walks-63dfd1f.txt
- [x] Test: a check runs the saved search for a watchlist with zero trials, and reports its failure separately from the trial checks (design 9/F) — test: test_a_check_runs_the_saved_search_even_with_no_trials; test: test_a_saved_search_failure_is_reported_apart_from_the_trials
- [x] Walk: a watchlist with a saved search and no trials offers "Check for new matches" (design 11/F) — walk: test_walk_a_watchlist_with_a_saved_search_and_no_trials_offers_check_for_new_matches; red: .scratch/html-front-end/red/11-walks-63dfd1f.txt
- [x] Walk: when the saved search found more than 100, the New matches tab and the check result say so — walk: test_walk_a_search_that_found_more_than_a_hundred_says_so_on_the_tab_and_in_the_check_result; test: test_a_search_matching_more_than_a_hundred_offers_a_hundred_and_says_the_cap_applied; red: .scratch/html-front-end/red/11-walks-63dfd1f.txt; red: .scratch/html-front-end/red/11-unit-d223300.txt

## Comments
