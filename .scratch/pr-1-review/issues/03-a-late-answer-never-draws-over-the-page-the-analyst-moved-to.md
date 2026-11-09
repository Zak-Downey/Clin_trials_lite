# 03: A late answer never draws over the page the analyst moved to, and the sidebar keeps its mark

**Blocked by:** 01, 02

**Status:** ready-for-agent

**Touches:** webapp/static/app.js, webapp/static/views/trial.js, webapp/static/views/needs_review.js, webapp/static/views/all_trials.js, webapp/static/views/summary.js

**Kind:** design

**Spec sections (read these, not this ticket's paraphrase):** Findings › F4, F5. Root: User Stories 3, 6, 36; Design coverage 1/1.

**What to build:** `route()` hands every render the `alive` it already gives Find trials and Registry details; the trial page, Needs review, All trials and Summary return before drawing when the analyst has moved on, and so does the sidebar. The sidebar redraw on `reviewchange` keeps the watchlist the address names marked as current.

- [x] Walk: with the trial's answer delayed, opening a trial and then another watchlist leaves the other watchlist's page drawn, matching the address — walk: test_walk_a_delayed_trial_answer_leaves_the_watchlist_the_address_names; red: .scratch/pr-1-review/red/03-walks-0a2ca89.txt
- [x] Walk: the same holds for Needs review, All trials and Summary: a delayed answer for a tab already left does not replace the page the address names — walk: test_walk_a_delayed_answer_for_a_tab_already_left_does_not_replace_the_page_the_address_names; red: .scratch/pr-1-review/red/03-walks-0a2ca89.txt
- [x] Walk: after Rename from the header menu, the open watchlist keeps `aria-current="page"` and its highlight in the sidebar — walk: test_walk_rename_from_the_header_menu_keeps_the_open_watchlist_marked_in_the_sidebar; red: .scratch/pr-1-review/red/03-walks-0a2ca89.txt
- [x] Walk: after + New watchlist, Remove from this list and its Undo, the open watchlist keeps `aria-current="page"` in the sidebar — walk: test_walk_new_watchlist_keeps_the_open_watchlist_marked_in_the_sidebar; walk: test_walk_removing_a_trial_and_its_undo_leave_the_sidebar_marking_where_the_address_points; red: .scratch/pr-1-review/red/03-walks-0a2ca89.txt

## Comments
