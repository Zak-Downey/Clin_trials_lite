# 08: Find trials: select results and add them to a watchlist

**Blocked by:** 05, 07

**Status:** done

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 62–68; Implementation Decisions › Domain changes ("Details of a trial that is not monitored", bulk add), › API (Membership); Design coverage 6/3, 6/4, 8/4.

**What to build:** Selecting and adding from search results. Each result row has a real checkbox and a "View details" title link; "Select 10 on this page" selects the page. Selections survive paging, viewing a trial and leaving and returning to Find trials. An action bar appears with the count, Clear, an "Add to" picker preset to the watchlist the analyst came from, and "Add N trials"; it reserves space below the results. Adding reports exactly what happened and clears the completed selection. The details of a trial not yet monitored come from one registry fetch, shown with the same sections as a monitored trial and an Add to watchlist action.

- [x] Walk: each result has a real checkbox and a separate title link; ticking never opens, and the link never selects; long titles wrap (design 6/3) — walk: test_walk_each_result_has_a_real_checkbox_and_a_separate_title_link_and_long_titles_wrap; red: .scratch/html-front-end/red/08-walks-6b05a7f.txt
- [x] Walk: "Select 10 on this page" selects only the current page; selections survive paging, opening a result's details and coming back, and leaving Find trials for Watchlists and returning, with the total selected stated (design 6/3, 6/F) — walk: test_walk_select_ten_on_this_page_selects_only_the_page_and_selections_survive_paging_details_and_leaving; red: .scratch/html-front-end/red/08-walks-6b05a7f.txt
- [x] Walk: once something is selected an action bar shows "N trials selected", Clear, "Add to <watchlist>" and "Add N trials", and the last result can still be scrolled clear of it (design 6/4) — walk: test_walk_the_action_bar_names_count_clear_and_destination_and_leaves_the_last_result_reachable; red: .scratch/html-front-end/red/08-walks-6b05a7f.txt
- [x] Walk: opened from a watchlist's "Add trials", the destination is preset to that watchlist (design 6/4) — walk: test_walk_opened_from_add_trials_the_destination_is_that_watchlist; red: .scratch/html-front-end/red/08-walks-6b05a7f.txt
- [x] Test: adding several trials returns which were added, which were already in the watchlist and which failed, by NCT ID — test: test_adding_several_trials_reports_which_were_added_which_were_already_there_and_which_failed; red: .scratch/html-front-end/red/08-unit-6b05a7f.txt
- [x] Walk: adding shows "N added; M already in this list" with a link to the watchlist, and clears the selection that was added (design 8/4) — walk: test_walk_adding_reports_added_and_already_in_this_list_links_the_watchlist_and_clears_the_selection; red: .scratch/html-front-end/red/08-walks-6b05a7f.txt
- [x] Walk: a newly added trial appears in All trials with "No changes" and does not enter Needs review — walk: test_walk_a_newly_added_trial_is_monitored_with_no_changes_and_does_not_enter_needs_review; red: .scratch/html-front-end/red/08-walks-6b05a7f.txt; needs-human: the All trials tab is ticket 06 (in flight), so the walk shows the trial in the sidebar count, absent from Needs review, and on its trial page with no unreviewed changes and a Monitoring started entry; re-check "No changes" in All trials once 06 merges
- [x] Walk: "View details" on a result not yet monitored shows its header facts and Trial details sections with no Changes or History tabs, and an "Add to watchlist" action; nothing is stored until it is added — walk: test_walk_view_details_of_a_trial_not_monitored_shows_sections_without_changes_or_history_and_stores_nothing_until_added; test: test_details_of_a_trial_not_monitored_come_from_the_registry_and_store_nothing; red: .scratch/html-front-end/red/08-walks-6b05a7f.txt; red: .scratch/html-front-end/red/08-unit-6b05a7f.txt

## Comments
