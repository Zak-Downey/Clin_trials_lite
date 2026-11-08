# 06: All trials: the whole watchlist, easy to scan

**Blocked by:** 03, 05

**Status:** done

**Touches:** webapp/static/app.js, webapp/static/style.css, webapp/routes.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 25–30; Design coverage 2/*.

**What to build:** The All trials tab: one row per trial with its title link, phase and sponsor, registry status, review state and last successful check (with a failure warning). A filter that searches only this watchlist and says so, and sorting by title, latest change or trial status. A title opens the trial on Trial details. The tab the analyst chooses is remembered; the default entry stays Needs review.

- [x] Walk: All trials lists every trial with title, phase and sponsor, registry status, review state and last successful check; headers stay visible while scrolling and long titles wrap onto taller rows (design 2/4) — walk: test_walk_all_trials_lists_every_trial_with_its_facts_headers_stay_and_titles_wrap; red: .scratch/html-front-end/red/06-walks-6a11c39-sticky.txt; test: test_all_trials_lists_every_trial_with_review_state_freshness_and_failure; test: test_a_trial_with_no_changes_reads_no_changes; red: .scratch/html-front-end/red/06-unit-6b05a7f.txt
- [x] Walk: the review state reads "N changes", "Reviewed" or "No changes", independent of the registry status in its own column (design 2/2) — walk: test_walk_the_review_state_is_separate_from_the_registry_status; red: .scratch/html-front-end/red/06-walks-6a11c39-d.txt; test: test_all_trials_lists_every_trial_with_review_state_freshness_and_failure; red: .scratch/html-front-end/red/06-unit-6b05a7f.txt
- [x] Walk: a trial whose latest check failed shows a labelled warning and keeps its earlier last-successful time (design 2/3) — walk: test_walk_a_failed_check_is_labelled_and_keeps_the_earlier_success_time; red: .scratch/html-front-end/red/06-walks-6a11c39-c.txt
- [x] Walk: "Filter by title, NCT ID or sponsor" narrows the table to this watchlist's matching trials and is labelled as separate from searching ClinicalTrials.gov (design 2/1) — walk: test_walk_the_filter_searches_only_this_watchlist_and_says_so; red: .scratch/html-front-end/red/06-walks-6a11c39-c.txt
- [x] Walk: sorting by title, latest change and trial status each reorder the table — walk: test_walk_sorting_by_title_latest_change_and_trial_status_reorders_the_table; red: .scratch/html-front-end/red/06-walks-6a11c39-d.txt
- [x] Walk: a title opens the trial on Trial details, with Changes available at once (design 2/4) — walk: test_walk_a_title_opens_trial_details_with_changes_one_click_away; red: .scratch/html-front-end/red/06-walks-6a11c39-b.txt
- [x] Walk: a watchlist opens on Needs review; choosing All trials, leaving and returning keeps All trials; a check or review that changes the counts does not switch the tab (design 2/F) — walk: test_walk_a_watchlist_opens_on_needs_review_and_remembers_all_trials; red: .scratch/html-front-end/red/06-walks-6a11c39-b.txt

## Comments
