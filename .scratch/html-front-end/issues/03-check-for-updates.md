# 03: Check for updates, with honest progress, failure and completion states

**Blocked by:** 02

**Status:** ready-for-agent

**Touches:** storage.py, monitor.py, webapp/static/app.js, webapp/static/style.css, webapp/routes.py, walks/standin_registry.py

**Spec sections (read these, not this ticket's paraphrase):** User Stories 14–24; Implementation Decisions › Domain changes ("Check failures persist per trial", "Retry failed"), › API (Checks); Design coverage 1/4, 2/3, 12/*.

**What to build:** The watchlist header shows its name, trial count and last-checked time, with "Check for updates" and "Add trials" (the latter opens Find trials with this watchlist as destination; Find trials itself arrives in 07). Pressing Check for updates runs the check on a server thread while the analyst keeps reading; the page polls progress. The status area shows the four states of design page 12. A failed check is recorded against the trial without moving its last successful check; Retry failed re-checks only those trials. The saved search's outcome is reported apart from the trials'.

- [x] Walk: the header shows the watchlist name, "N trials monitored" and "Last checked <local time>", and the only checking control is "Check for updates", with no wording implying scheduled or live monitoring (design 1/4) — walk: test_walk_the_header_names_the_watchlist_and_offers_only_a_manual_check; red: .scratch/html-front-end/red/03-walks-a348fc2.txt
- [x] Walk: during a check, "Checking for updates…" shows "N of M trials checked" and what runs next with a progress bar, while the queue and an open trial stay readable and usable (design 12/1) — walk: test_walk_during_a_check_progress_shows_and_the_queue_and_a_trial_stay_usable; red: .scratch/html-front-end/red/03-walks-a348fc2.txt
- [x] Test: a second check for the same watchlist is refused while one runs; walk: the button is disabled with its reason while a check runs (design 12/1) — test: test_a_second_check_for_the_same_watchlist_is_refused_while_one_runs; walk: test_walk_during_a_check_progress_shows_and_the_queue_and_a_trial_stay_usable; red: .scratch/html-front-end/red/03-unit-a348fc2.txt; red: .scratch/html-front-end/red/03-walks-a348fc2.txt
- [x] Walk: a check where the stand-in fails one trial shows "Check incomplete", "N of M trials checked · 1 trial could not be checked", the saved search's outcome on its own line, "Retry failed" and "Show details", and never an all-clear (design 12/2) — walk: test_walk_a_check_with_one_failed_trial_is_incomplete_and_never_an_all_clear; test: test_a_saved_search_failure_is_reported_apart_from_the_trials; red: .scratch/html-front-end/red/03-walks-a348fc2.txt; red: .scratch/html-front-end/red/03-unit-a348fc2.txt
- [x] Test: a failed check records its time and error kind on the trial and leaves its last successful check unchanged; a later success clears the failure (design 2/3, 12/2) — test: test_a_failed_check_records_its_time_and_kind_and_a_later_success_clears_it; red: .scratch/html-front-end/red/03-unit-a348fc2.txt
- [x] Test: Retry failed re-checks only the trials whose check failed in the watchlist's last check run — test: test_retry_failed_rechecks_only_the_failed_trials; test: test_retry_failed_rechecks_only_the_trials_that_failed_in_the_last_run; red: .scratch/html-front-end/red/03-unit-a348fc2.txt
- [x] Walk: a check that finds nothing new says "Check complete · No new changes detected" with the number checked, the time, and "N trials still need review from earlier checks", and the queue keeps its earlier entries (design 12/3) — walk: test_walk_a_check_that_finds_nothing_says_so_and_keeps_earlier_entries_in_the_queue; red: .scratch/html-front-end/red/03-walks-a348fc2.txt
- [x] Walk: with nothing to review, Needs review shows "All caught up", "No changes awaiting review. Last checked <time>" and "View all trials", and the tab does not change by itself after a check (design 12/4) — walk: test_walk_with_nothing_to_review_the_queue_says_all_caught_up_and_stays_on_its_tab; red: .scratch/html-front-end/red/03-walks-a348fc2.txt
- [x] Test: a watchlist's last-checked time is when its most recent check for updates finished — test: test_a_watchlists_last_checked_is_when_its_most_recent_check_for_updates_finished; red: .scratch/html-front-end/red/03-unit-a348fc2.txt
- [x] Walk: after the stand-in's revise switch, Check for updates adds the changed trial to Needs review and the sidebar count rises, without the page switching tabs — walk: test_walk_a_revised_trial_joins_needs_review_after_a_check_without_a_tab_change; red: .scratch/html-front-end/red/03-walks-a348fc2.txt

## Comments
