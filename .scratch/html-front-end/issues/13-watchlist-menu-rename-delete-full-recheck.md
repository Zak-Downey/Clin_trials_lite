# 13: Watchlist menu: rename, delete and full recheck

**Blocked by:** 03, 05, 09

**Status:** done

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 93–96; Implementation Decisions › Domain changes ("Retention"); Design coverage 12/F, 13/1–13/4.

**What to build:** The watchlist's ⋯ menu with Rename watchlist, Manage saved search (ticket 10's dialog), Full recheck and Delete watchlist, each opening its own dialog. Rename checks names inline. Full recheck explains that it ignores the registry's update date and finishes with its own label. Delete names the watchlist, states exactly what goes and what stays, keeps history, and cannot be undone.

- [x] Walk: the ⋯ menu offers Rename watchlist, Manage saved search, Full recheck and Delete watchlist, and each opens its own dialog; no form both creates and renames or deletes (design 13/1) — walk: test_walk_the_menu_offers_four_actions_and_each_opens_its_own_dialog; red: .scratch/html-front-end/red/13-walks-af43ce8.txt
- [x] Walk: Rename shows the current name, refuses an empty or duplicate name inline, and Save or Cancel returns to the same view and scroll position (design 13/2) — walk: test_walk_rename_shows_the_current_name_refuses_empty_and_duplicate_inline_and_keeps_the_place; red: .scratch/html-front-end/red/13-walks-af43ce8.txt; test: test_rename_refuses_an_empty_or_duplicate_name_and_keeps_the_old_one; red: .scratch/html-front-end/red/13-unit-af43ce8.txt
- [x] Walk: Full recheck explains that it compares every monitored field even when the registry's update date has not moved, runs once, and finishes with its own completion label; normal checks are unaffected (design 13/4, 12/F) — walk: test_walk_full_recheck_explains_itself_runs_once_and_finishes_with_its_own_label; red: .scratch/html-front-end/red/13-walks-af43ce8.txt
- [x] Test: a normal check skips a trial whose registry update date has not moved, and a full recheck compares it anyway (design 12/F) — test: test_a_normal_check_skips_an_unmoved_stamp_and_a_full_recheck_compares_it_anyway; red: .scratch/html-front-end/red/13-unit-af43ce8.txt
- [x] Walk: Delete watchlist names it and says it removes the watchlist, its saved search and its memberships, that trials in other watchlists are unchanged, that history is kept while trials no longer in any watchlist stop being checked, and that it cannot be undone (design 13/3) — walk: test_walk_delete_names_the_watchlist_states_what_goes_and_stays_and_lands_on_another; red: .scratch/html-front-end/red/13-walks-af43ce8.txt
- [x] Test: deleting a watchlist keeps every trial's snapshots and changes, and trials still in another watchlist keep being checked (design 13/3) — test: test_deleting_a_watchlist_keeps_every_trials_history_and_trials_in_another_list_keep_being_checked; red: .scratch/html-front-end/red/13-unit-af43ce8.txt

## Comments
