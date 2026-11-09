# 10: Saved search: watch a search, replace it, manage it

**Blocked by:** 09

**Status:** ready-for-agent

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 72–76; Implementation Decisions › API (Saved search); Design coverage 1/5, 8/1, 8/2, 13/F.

**What to build:** "Watch this search" on the results opens a dialog that saves the submitted query to a chosen watchlist, with nothing selected required and no results added. If the watchlist already has a saved search, the dialog shows it and the button reads "Replace saved search". Success names the watchlist with Open watchlist. A watchlist with a saved search shows the "Saved search is on" banner with Manage, which shows the query with Edit search (Find trials pre-filled; replaces only when saved) and Turn off (keeps the trials).

- [x] Walk: "Watch this search" opens a dialog showing the submitted query and a watchlist picker, works with no result selected, and adds no trials (design 6/2, 8/1) — walk: test_walk_watch_this_search_saves_the_query_with_nothing_selected_to_an_empty_watchlist_and_adds_no_trials; test: test_saving_a_search_stores_it_and_adds_no_trials; red: .scratch/html-front-end/red/10-walks-cb2ceb7.txt; red: .scratch/html-front-end/red/10-unit-ee71b15.txt
- [x] Walk: a watchlist with no trials can be the target (design 8/1) — walk: test_walk_watch_this_search_saves_the_query_with_nothing_selected_to_an_empty_watchlist_and_adds_no_trials; red: .scratch/html-front-end/red/10-walks-cb2ceb7.txt
- [x] Walk: when the chosen watchlist already has a saved search, the dialog shows "This watchlist already has a saved search" with its current query, the button reads "Replace saved search", and Cancel leaves the old one in place (design 8/2) — walk: test_walk_a_watchlist_that_already_has_a_saved_search_shows_it_and_replace_is_deliberate; walk: test_walk_a_late_answer_for_an_earlier_watchlist_never_changes_the_dialog_for_the_one_now_chosen; red: .scratch/html-front-end/red/10-walks-cb2ceb7-late.txt; test: test_saving_again_replaces_and_reports_the_old_query; red: .scratch/html-front-end/red/10-walks-cb2ceb7.txt; red: .scratch/html-front-end/red/10-unit-ee71b15.txt
- [x] Walk: saving shows "Search saved", that the watchlist will check for new matches when you run Check for updates, and "Open watchlist" (design 8/4) — walk: test_walk_watch_this_search_saves_the_query_with_nothing_selected_to_an_empty_watchlist_and_adds_no_trials; red: .scratch/html-front-end/red/10-walks-cb2ceb7.txt
- [x] Walk: a watchlist with a saved search shows "Saved search is on", that it runs when you check for updates and new matches need your approval, and Manage; it sits above the tabs and does not push the Needs review list down (design 1/5) — walk: test_walk_a_saved_search_banner_sits_above_the_tabs_and_leaves_the_review_list_in_view; red: .scratch/html-front-end/red/10-walks-cb2ceb7.txt
- [x] Walk: Manage shows the query, "Edit search" and "Turn off"; Edit search opens Find trials pre-filled and replaces the saved query only when saved; Turn off removes the banner and keeps every trial (design 13/F) — walk: test_walk_manage_shows_the_query_edit_search_prefills_find_and_turn_off_keeps_every_trial; test: test_turning_off_removes_the_search_and_keeps_the_trials; red: .scratch/html-front-end/red/10-walks-cb2ceb7.txt; red: .scratch/html-front-end/red/10-unit-ee71b15.txt

## Comments
